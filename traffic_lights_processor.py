"""
Traffic Lights Geometric Selection Program
===========================================

Program do przetwarzania danych traffic lights z selekcją geometryczną.
Funkcjonalność:
- Import plików CSV z geometrią punktową traffic lights
- Import plików GPKG z geometrią liniową dróg
- Import plików GPKG z geometrią polygonową bufforów
- Selekcja skrzyżowań intersektujących polygon
- Filtracja traffic lights intersektujących polygon
- Inteligentne grupowanie objektów (50-70 per grupę)
- Zapis nieusatysfakcjonowanych punktów do pliku output_2_unmatched.gpkg
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import cdist
import logging
from datetime import datetime
import json
import sys
from shapely.geometry import Point

# Konfiguracja logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'traffic_lights_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TrafficLightsProcessor:
    """
    Główna klasa do przetwarzania danych traffic lights i wykonywania selekcji geometrycznej.
    """

    def __init__(self, config_path='config.json'):
        """
        Inicjalizacja procesora.
        
        Args:
            config_path (str): Ścieżka do pliku konfiguracyjnego
        """
        self.config = self.load_config(config_path)
        self.traffic_lights = None
        self.roads = None
        self.buffers = None
        self.intersected_roads = None
        self.matched_lights = None
        self.unmatched_lights = None
        self.grouped_lights = None
        
        logger.info("TrafficLightsProcessor zainicjalizowany")

    @staticmethod
    def load_config(config_path):
        """
        Załadowanie konfiguracji z pliku JSON.
        
        Args:
            config_path (str): Ścieżka do pliku config.json
            
        Returns:
            dict: Załadowana konfiguracja
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Konfiguracja załadowana z: {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Plik konfiguracyjny nie znaleziony: {config_path}")
            raise

    def load_traffic_lights(self):
        """
        Załadowanie pliku CSV z traffic lights i konwersja do GeoDataFrame.
        """
        try:
            csv_path = self.config['input_files']['traffic_lights_csv']
            logger.info(f"Ładowanie traffic lights z: {csv_path}")
            
            df = pd.read_csv(csv_path)
            
            # Konwersja do GeoDataFrame
            geometry = gpd.points_from_xy(df[self.config['csv_columns']['lon']], 
                                          df[self.config['csv_columns']['lat']])
            self.traffic_lights = gpd.GeoDataFrame(
                df,
                geometry=geometry,
                crs=self.config['crs']
            )
            
            logger.info(f"Załadowano {len(self.traffic_lights)} traffic lights")
            logger.info(f"CRS: {self.traffic_lights.crs}")
            
        except Exception as e:
            logger.error(f"Błąd przy ładowaniu traffic lights: {e}")
            raise

    def load_roads(self):
        """
        Załadowanie pliku GPKG z geometrią liniową dróg.
        """
        try:
            roads_path = self.config['input_files']['roads_gpkg']
            logger.info(f"Ładowanie dróg z: {roads_path}")
            
            self.roads = gpd.read_file(roads_path)
            logger.info(f"Załadowano {len(self.roads)} drogi")
            logger.info(f"CRS: {self.roads.crs}")
            
        except Exception as e:
            logger.error(f"Błąd przy ładowaniu dróg: {e}")
            raise

    def load_buffers(self):
        """
        Załadowanie pliku GPKG z geometrią polygonową bufforów.
        """
        try:
            buffers_path = self.config['input_files']['buffers_gpkg']
            logger.info(f"Ładowanie bufforów z: {buffers_path}")
            
            self.buffers = gpd.read_file(buffers_path)
            logger.info(f"Załadowano {len(self.buffers)} buffery")
            logger.info(f"CRS: {self.buffers.crs}")
            
        except Exception as e:
            logger.error(f"Błąd przy ładowaniu bufforów: {e}")
            raise

    def ensure_same_crs(self):
        """
        Zapewnienie tego samego CRS dla wszystkich danych.
        """
        target_crs = self.config['crs']
        
        if self.traffic_lights.crs != target_crs:
            logger.info(f"Transformacja traffic lights do CRS: {target_crs}")
            self.traffic_lights = self.traffic_lights.to_crs(target_crs)
            
        if self.roads.crs != target_crs:
            logger.info(f"Transformacja dróg do CRS: {target_crs}")
            self.roads = self.roads.to_crs(target_crs)
            
        if self.buffers.crs != target_crs:
            logger.info(f"Transformacja bufforów do CRS: {target_crs}")
            self.buffers = self.buffers.to_crs(target_crs)
        
        logger.info("Wszystkie dane w jednakowym CRS")

    def select_intersected_roads(self):
        """
        Selekcja dróg które intersektują polygon buffora.
        """
        logger.info("Selekcja dróg intersektujących polygon")
        
        self.intersected_roads = gpd.sjoin(
            self.roads,
            self.buffers,
            how='inner',
            predicate='intersects'
        )
        
        # Usunięcie duplikatów (droga może intersektować wiele bufforów)
        self.intersected_roads = self.intersected_roads.drop_duplicates(
            subset=['geometry'], keep='first'
        )
        
        logger.info(f"Wybrano {len(self.intersected_roads)} dróg intersektujących polygon")
        
        return self.intersected_roads

    def select_matched_traffic_lights(self):
        """
        Selekcja traffic lights które intersektują polygon buffora.
        """
        logger.info("Selekcja traffic lights intersektujących polygon")
        
        matched = gpd.sjoin(
            self.traffic_lights,
            self.buffers,
            how='inner',
            predicate='intersects'
        )
        
        self.matched_lights = matched.drop_duplicates(
            subset=['geometry'], keep='first'
        )
        
        # Usunięcie kolumn z indeksami z sjoin
        cols_to_keep = [col for col in self.traffic_lights.columns if col in self.matched_lights.columns]
        self.matched_lights = self.matched_lights[cols_to_keep]
        
        logger.info(f"Wybrano {len(self.matched_lights)} traffic lights intersektujących polygon")
        
        return self.matched_lights

    def identify_unmatched_lights(self):
        """
        Identyfikacja traffic lights które nie intersektują polygon.
        """
        logger.info("Identyfikacja traffic lights które nie intersektują polygon")
        
        if self.matched_lights is None:
            self.select_matched_traffic_lights()
        
        matched_indices = set(self.matched_lights.index)
        all_indices = set(self.traffic_lights.index)
        unmatched_indices = all_indices - matched_indices
        
        self.unmatched_lights = self.traffic_lights.loc[list(unmatched_indices)].copy()
        
        logger.info(f"Znaleziono {len(self.unmatched_lights)} traffic lights poza polygonem")
        
        return self.unmatched_lights

    def group_lights_by_proximity(self, min_group_size=50, max_group_size=70, 
                                   epsilon=1000, min_samples=3):
        """
        Grupowanie traffic lights z uwzględnieniem ich bliskości przestrzennej.
        """
        logger.info(f"Grupowanie traffic lights (rozmiar grupy: {min_group_size}-{max_group_size})")
        
        if self.matched_lights is None or len(self.matched_lights) == 0:
            logger.warning("Brak matched_lights do grupowania")
            return
        
        coords = np.array([[geom.x, geom.y] for geom in self.matched_lights.geometry])
        
        logger.info("Aplikacja DBSCAN dla znalezienia klastrów geograficznych")
        dbscan = DBSCAN(eps=epsilon, min_samples=min_samples)
        clusters = dbscan.fit_predict(coords)
        
        lights_with_clusters = self.matched_lights.copy()
        lights_with_clusters['cluster'] = clusters
        lights_with_clusters['group'] = -1
        
        group_id = 0
        n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)
        logger.info(f"Znaleziono {n_clusters} klastrów geograficznych")
        
        for cluster_id in sorted(set(clusters)):
            if cluster_id == -1:
                logger.warning(f"Znaleziono {len(lights_with_clusters[lights_with_clusters['cluster'] == -1])} punktów szumu")
                continue
            
            cluster_lights = lights_with_clusters[lights_with_clusters['cluster'] == cluster_id].copy()
            logger.info(f"Przetwarzanie klastra {cluster_id} z {len(cluster_lights)} objektów")
            
            if len(cluster_lights) > max_group_size:
                subgroups = self._subdivide_cluster(cluster_lights, min_group_size, max_group_size)
            else:
                subgroups = [cluster_lights]
            
            for subgroup in subgroups:
                lights_with_clusters.loc[subgroup.index, 'group'] = group_id
                logger.info(f"Grupa {group_id}: {len(subgroup)} objektów")
                group_id += 1
        
        self.grouped_lights = lights_with_clusters
        logger.info(f"Stworzono {group_id} grup traffic lights")
        
        return self.grouped_lights

    def _subdivide_cluster(self, cluster_gdf, min_size, max_size):
        """
        Podział dużego klastra na mniejsze grupy.
        """
        if len(cluster_gdf) <= max_size:
            return [cluster_gdf]
        
        subgroups = []
        coords = np.array([[geom.x, geom.y] for geom in cluster_gdf.geometry])
        
        sub_dbscan = DBSCAN(eps=500, min_samples=2)
        sub_clusters = sub_dbscan.fit_predict(coords)
        
        cluster_gdf_temp = cluster_gdf.copy()
        cluster_gdf_temp['subcluster'] = sub_clusters
        
        for subcluster_id in sorted(set(sub_clusters)):
            if subcluster_id == -1:
                continue
            
            subcluster_lights = cluster_gdf_temp[cluster_gdf_temp['subcluster'] == subcluster_id]
            
            if len(subcluster_lights) > max_size:
                further_divided = self._subdivide_cluster(
                    subcluster_lights.drop('subcluster', axis=1),
                    min_size,
                    max_size
                )
                subgroups.extend(further_divided)
            else:
                subgroups.append(subcluster_lights.drop('subcluster', axis=1))
        
        return subgroups

    def save_unmatched_lights(self, output_path=None):
        """
        Zapis traffic lights które nie intersektują polygon.
        """
        if output_path is None:
            output_path = self.config['output_files']['unmatched_gpkg']
        
        if self.unmatched_lights is None:
            self.identify_unmatched_lights()
        
        logger.info(f"Zapis {len(self.unmatched_lights)} traffic lights do: {output_path}")
        
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.unmatched_lights.to_file(output_path, driver='GPKG')
        logger.info(f"Plik zapisany: {output_path}")

    def save_grouped_lights(self, output_dir=None):
        """
        Zapis pogrupowanych traffic lights do osobnych plików.
        """
        if output_dir is None:
            output_dir = self.config['output_files']['groups_dir']
        
        if self.grouped_lights is None:
            logger.error("Brak pogrupowanych danych")
            return
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Zapis pogrupowanych traffic lights do: {output_dir}")
        
        for group_id in sorted(self.grouped_lights['group'].unique()):
            if group_id == -1:
                continue
            
            group_data = self.grouped_lights[self.grouped_lights['group'] == group_id]
            output_file = output_path / f"traffic_lights_group_{group_id:03d}.gpkg"
            
            group_data.to_file(str(output_file), driver='GPKG')
            logger.info(f"Grupa {group_id}: {len(group_data)} objektów")

    def save_matched_lights(self, output_path=None):
        """
        Zapis wszystkich matched traffic lights.
        """
        if output_path is None:
            output_path = self.config['output_files']['matched_gpkg']
        
        if self.matched_lights is None:
            self.select_matched_traffic_lights()
        
        logger.info(f"Zapis {len(self.matched_lights)} traffic lights do: {output_path}")
        
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.matched_lights.to_file(output_path, driver='GPKG')
        logger.info(f"Plik zapisany: {output_path}")

    def generate_report(self, output_path=None):
        """
        Generacja raportu przetwarzania.
        """
        if output_path is None:
            output_path = self.config['output_files']['report_txt']
        
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report = []
        report.append("=" * 70)
        report.append("RAPORT PRZETWARZANIA TRAFFIC LIGHTS")
        report.append("=" * 70)
        report.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("STATYSTYKI DANYCH WEJŚCIOWYCH:")
        report.append(f"  - Traffic lights załadowane: {len(self.traffic_lights) if self.traffic_lights is not None else 'N/A'}")
        report.append(f"  - Drogi załadowane: {len(self.roads) if self.roads is not None else 'N/A'}")
        report.append(f"  - Buffery załadowane: {len(self.buffers) if self.buffers is not None else 'N/A'}")
        report.append("")
        
        report.append("WYNIKI SELEKCJI:")
        report.append(f"  - Drogi intersektujące polygon: {len(self.intersected_roads) if self.intersected_roads is not None else 'N/A'}")
        report.append(f"  - Traffic lights intersektujące polygon: {len(self.matched_lights) if self.matched_lights is not None else 'N/A'}")
        report.append(f"  - Traffic lights poza polygonem: {len(self.unmatched_lights) if self.unmatched_lights is not None else 'N/A'}")
        report.append("")
        
        if self.grouped_lights is not None:
            n_groups = len(set(self.grouped_lights[self.grouped_lights['group'] != -1]['group']))
            report.append("GRUPOWANIE:")
            report.append(f"  - Liczba grup: {n_groups}")
        
        report.append("=" * 70)
        
        report_text = "\n".join(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"Raport zapisany do: {output_path}")
        print(report_text)

    def run_full_pipeline(self):
        """
        Uruchomienie pełnego pipeline'u przetwarzania.
        """
        logger.info("Uruchamianie pełnego pipeline'u przetwarzania")
        
        try:
            self.load_traffic_lights()
            self.load_roads()
            self.load_buffers()
            self.ensure_same_crs()
            self.select_intersected_roads()
            self.select_matched_traffic_lights()
            self.identify_unmatched_lights()
            
            self.group_lights_by_proximity(
                min_group_size=self.config['grouping']['min_group_size'],
                max_group_size=self.config['grouping']['max_group_size'],
                epsilon=self.config['grouping']['epsilon'],
                min_samples=self.config['grouping']['min_samples']
            )
            
            self.save_matched_lights()
            self.save_unmatched_lights()
            self.save_grouped_lights()
            self.generate_report()
            
            logger.info("Pipeline przetwarzania zakończony pomyślnie")
            
        except Exception as e:
            logger.error(f"Błąd: {e}", exc_info=True)
            raise


def main():
    try:
        processor = TrafficLightsProcessor('config.json')
        processor.run_full_pipeline()
    except Exception as e:
        logger.error(f"Błąd: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
