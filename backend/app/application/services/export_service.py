import io
import os
import zipfile
import tempfile
import uuid
from typing import List, Dict, Any, Optional
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping
from geoalchemy2.shape import to_shape
from app.infrastructure.external.minio_client import MinioStorageClient

class ExportService:
    def __init__(self, minio_client: Optional[MinioStorageClient] = None):
        self.minio_client = minio_client or MinioStorageClient()

    def generate_geojson(self, cells: List[Any], hotspots: List[Any]) -> Dict[str, Any]:
        """
        Creates a unified GeoJSON FeatureCollection containing all H3 cells
        and their associated damage scores, classes, and hotspot properties.
        """
        # Map hotspots by h3_index for quick lookup
        hs_map = {
            h.h3_index: {
                "z_score": round(float(h.intensity), 4) if h.intensity is not None else 0.0,
                "p_value": round(float(h.confidence), 4) if h.confidence is not None else 1.0,
                "hotspot_class": h.classification or "Anlamsız (Nötr)"
            }
            for h in hotspots
        }

        features = []
        for cell in cells:
            geom_shape = to_shape(cell.geometry)
            hs_info = hs_map.get(cell.h3_index, {
                "z_score": 0.0,
                "p_value": 1.0,
                "hotspot_class": "Nötr"
            })

            features.append({
                "type": "Feature",
                "geometry": mapping(geom_shape),
                "properties": {
                    "h3_index": cell.h3_index,
                    "damage_score": round(float(cell.damage_score), 4),
                    "damage_percent": f"{round(float(cell.damage_score) * 100, 1)}%",
                    "damage_class": cell.damage_class or "Yok",
                    "hotspot_class": hs_info["hotspot_class"],
                    "hotspot_z_score": hs_info["z_score"],
                    "hotspot_p_value": hs_info["p_value"]
                }
            })

        return {
            "type": "FeatureCollection",
            "count": len(features),
            "features": features
        }

    def generate_csv(self, cells: List[Any], hotspots: List[Any]) -> str:
        """
        Generates a clean, Excel-compatible CSV string with all grid cell records.
        """
        hs_map = {
            h.h3_index: {
                "z_score": round(float(h.intensity), 4) if h.intensity is not None else 0.0,
                "p_value": round(float(h.confidence), 4) if h.confidence is not None else 1.0,
                "hotspot_class": h.classification or "Nötr"
            }
            for h in hotspots
        }

        rows = []
        for cell in cells:
            geom_shape = to_shape(cell.geometry)
            centroid = geom_shape.centroid
            hs_info = hs_map.get(cell.h3_index, {
                "z_score": 0.0,
                "p_value": 1.0,
                "hotspot_class": "Nötr"
            })

            rows.append({
                "H3_Indeks": cell.h3_index,
                "Enlem": round(centroid.y, 6),
                "Boylam": round(centroid.x, 6),
                "Hasar_Skoru": round(float(cell.damage_score), 4),
                "Hasar_Yuzdesi": f"{round(float(cell.damage_score) * 100, 1)}%",
                "Hasar_Sinifi": cell.damage_class or "Yok",
                "Hotspot_Sinifi": hs_info["hotspot_class"],
                "Z_Skoru": hs_info["z_score"],
                "P_Degeri": hs_info["p_value"]
            })

        df = pd.DataFrame(rows)
        return df.to_csv(index=False, encoding="utf-8-sig")

    def generate_shapefile_zip(self, cells: List[Any], hotspots: List[Any]) -> bytes:
        """
        Generates a zipped ESRI Shapefile archive containing .shp, .shx, .dbf, .prj.
        """
        hs_map = {
            h.h3_index: {
                "z_score": round(float(h.intensity), 4) if h.intensity is not None else 0.0,
                "p_value": round(float(h.confidence), 4) if h.confidence is not None else 1.0,
                "hs_class": h.classification or "Notr"
            }
            for h in hotspots
        }

        geometries = []
        data = []
        for cell in cells:
            geom = to_shape(cell.geometry)
            geometries.append(geom)
            hs_info = hs_map.get(cell.h3_index, {"z_score": 0.0, "p_value": 1.0, "hs_class": "Notr"})
            data.append({
                "h3_idx": cell.h3_index,
                "dmg_score": float(cell.damage_score),
                "dmg_class": str(cell.damage_class or "Yok"),
                "hs_class": str(hs_info["hs_class"]),
                "z_score": float(hs_info["z_score"]),
                "p_value": float(hs_info["p_value"])
            })

        gdf = gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = os.path.join(tmpdir, "damage_assessment.shp")
            gdf.to_file(shp_path, driver="ESRI Shapefile")

            # Create in-memory zip
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_name in os.listdir(tmpdir):
                    file_path = os.path.join(tmpdir, file_name)
                    zf.write(file_path, arcname=file_name)

            return zip_buffer.getvalue()

    def generate_geopackage(self, cells: List[Any], hotspots: List[Any]) -> bytes:
        """
        Generates an OGC standard GeoPackage (.gpkg) file with damage_cells and hotspots layers.
        """
        # Layer 1: Damage Cells
        cell_geoms = [to_shape(c.geometry) for c in cells]
        cell_data = [{
            "h3_index": c.h3_index,
            "damage_score": float(c.damage_score),
            "damage_class": str(c.damage_class or "Yok")
        } for c in cells]
        cells_gdf = gpd.GeoDataFrame(cell_data, geometry=cell_geoms, crs="EPSG:4326")

        # Layer 2: Hotspots
        hs_geoms = [to_shape(h.geometry) for h in hotspots]
        hs_data = [{
            "h3_index": h.h3_index,
            "intensity_z": float(h.intensity) if h.intensity is not None else 0.0,
            "confidence_p": float(h.confidence) if h.confidence is not None else 1.0,
            "classification": str(h.classification or "Notr")
        } for h in hotspots]
        hs_gdf = gpd.GeoDataFrame(hs_data, geometry=hs_geoms, crs="EPSG:4326")

        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg_path = os.path.join(tmpdir, "damage_assessment.gpkg")
            if not cells_gdf.empty:
                cells_gdf.to_file(gpkg_path, layer="damage_cells", driver="GPKG")
            if not hs_gdf.empty:
                hs_gdf.to_file(gpkg_path, layer="hotspots", driver="GPKG", mode="a" if not cells_gdf.empty else "w")

            with open(gpkg_path, "rb") as f:
                return f.read()

    def get_raster_download_info(self, job_id: uuid.UUID, layer: str, artifacts: List[Any]) -> Dict[str, Any]:
        """
        Finds the corresponding GeoTIFF artifact and returns its presigned URL and filename.
        """
        type_mapping = {
            "fusion": "FUSION_TIFF",
            "sar": "SAR_TIFF",
            "ms": "MS_TIFF"
        }
        target_type = type_mapping.get(layer.lower(), "FUSION_TIFF")

        target_artifact = None
        for art in artifacts:
            if art.file_type == target_type:
                target_artifact = art
                break

        if not target_artifact:
            # Fallback to local file if exists
            local_path = f"temp_downloads/fusion_result_{job_id}.tif" if target_type == "FUSION_TIFF" else None
            return {
                "found": os.path.exists(local_path) if local_path else False,
                "minio_key": None,
                "download_url": None,
                "local_path": local_path
            }

        download_url = None
        try:
            download_url = self.minio_client.get_presigned_download_url(target_artifact.minio_key, expires_seconds=3600)
        except Exception:
            pass

        return {
            "found": True,
            "minio_key": target_artifact.minio_key,
            "download_url": download_url,
            "file_type": target_artifact.file_type
        }
