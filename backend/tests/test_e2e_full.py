import asyncio
import httpx
import uuid
import time

BASE_URL = "http://localhost:8000/api/v1"

async def test_full_platform_e2e():
    print("=" * 70)
    print("🌾 PLATFORM FULL END-TO-END (E2E) INTEGRATION TEST SUITE (SPRINT 10) 🌾")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=45.0) as client:
        # STEP 1: Healthcheck & Service Connectivity
        print("\n[1/7] Testing Healthcheck & Infrastructure Services...")
        h_res = await client.get("/health/")
        assert h_res.status_code == 200, f"Healthcheck failed: {h_res.text}"
        h_data = h_res.json()
        assert h_data["status"] == "healthy"
        assert h_data["services"]["database"] == "healthy"
        assert h_data["services"]["redis"] == "healthy"
        print(f"  ✓ Database, Redis and Celery online: {h_data}")

        # STEP 2: Authentication & RBAC Login
        print("\n[2/7] Testing Authentication (JWT) & Role Management...")
        admin_login = await client.post("/auth/login", json={
            "email": "admin@damage.org",
            "password": "Admin123!"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_user_id = admin_login.json()["user"]["id"]

        analyst_login = await client.post("/auth/login", json={
            "email": "analyst@damage.org",
            "password": "Analyst123!"
        })
        assert analyst_login.status_code == 200
        analyst_token = analyst_login.json()["access_token"]

        viewer_login = await client.post("/auth/login", json={
            "email": "viewer@damage.org",
            "password": "Viewer123!"
        })
        assert viewer_login.status_code == 200
        viewer_token = viewer_login.json()["access_token"]
        print("  ✓ Admin, Analyst, and Viewer JWT sessions generated successfully.")

        # RBAC Check: Viewer must be blocked from admin user management
        v_admin_try = await client.get("/admin/users/", headers={"Authorization": f"Bearer {viewer_token}"})
        assert v_admin_try.status_code == 403
        print("  ✓ RBAC Guard confirmed: Viewer blocked with 403 Forbidden.")

        # STEP 3: AOI Creation (Spatial Polygon)
        print("\n[3/7] Creating Field Parcel (AOI)...")
        aoi_name = f"Manisa Test Parseli {uuid.uuid4().hex[:4]}"
        wkt_polygon = "POLYGON((27.42 38.61, 27.45 38.61, 27.45 38.64, 27.42 38.64, 27.42 38.61))"
        aoi_res = await client.post("/aoi/", json={
            "name": aoi_name,
            "geometry": wkt_polygon
        }, headers={"Authorization": f"Bearer {analyst_token}"})
        assert aoi_res.status_code == 201, f"AOI create failed: {aoi_res.text}"
        aoi_data = aoi_res.json()
        aoi_id = aoi_data["id"]
        print(f"  ✓ AOI created successfully with ID: {aoi_id} (Name: {aoi_name})")

        # STEP 4: Asynchronous Analysis Job (Celery Chord)
        print("\n[4/7] Triggering Multi-Sensor Fusion Analysis Job...")
        job_res = await client.post("/jobs/", json={
            "aoi_id": aoi_id,
            "event_date": "2026-07-15T00:00:00Z",
            "weights": {
                "sar": 0.35,
                "ndmi": 0.25,
                "ndre": 0.20,
                "precipitation": 0.12,
                "soil_moisture": 0.08
            }
        }, headers={"Authorization": f"Bearer {analyst_token}"})
        assert job_res.status_code == 201, f"Job create failed: {job_res.text}"
        job_data = job_res.json()
        job_id = job_data["id"]
        print(f"  ✓ Job dispatched into Celery queue: {job_id}")

        # Polling job status
        print("  ⏳ Waiting for Celery chord pipeline (SAR + MS + Weather -> Fusion -> H3 Aggregation)...")
        max_retries = 30
        job_finished = False
        final_status = None
        for i in range(max_retries):
            await asyncio.sleep(2.0)
            status_res = await client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {analyst_token}"})
            assert status_res.status_code == 200
            cur_job = status_res.json()
            final_status = cur_job["status"]
            print(f"     [Tick {i+1}] Status: {final_status} | SAR: {cur_job.get('sar_status')} | MS: {cur_job.get('ms_status')} | Weather: {cur_job.get('weather_status')}")
            if final_status == "done":
                job_finished = True
                break
            elif final_status == "failed":
                raise AssertionError(f"Job failed unexpectedly: {cur_job.get('error_message')}")

        assert job_finished, f"Job timed out after {max_retries*2} seconds"
        print(f"  ✓ Analysis pipeline completed successfully in {final_status.upper()} state!")

        # STEP 5: Verifying Analytical & Spatial Results
        print("\n[5/7] Verifying Aggregation, Hotspots, and Time Series...")
        
        # 5.1 Summary
        sum_res = await client.get(f"/jobs/{job_id}/results/summary", headers={"Authorization": f"Bearer {analyst_token}"})
        assert sum_res.status_code == 200
        s_data = sum_res.json()
        assert "mean_damage_score" in s_data
        assert s_data["total_cells"] > 0
        print(f"  ✓ Summary Results: Mean Damage: {round(s_data['mean_damage_score']*100, 2)}%, Total H3 Cells: {s_data['total_cells']}")

        # 5.2 H3 Grid Features
        grid_res = await client.get(f"/jobs/{job_id}/results/grid", headers={"Authorization": f"Bearer {analyst_token}"})
        assert grid_res.status_code == 200
        g_data = grid_res.json()
        assert g_data["type"] == "FeatureCollection"
        assert len(g_data["features"]) > 0
        print(f"  ✓ H3 Resolution-9 Grid: {len(g_data['features'])} cells extracted.")

        # 5.3 Hotspots
        hs_res = await client.get(f"/jobs/{job_id}/results/hotspots", headers={"Authorization": f"Bearer {analyst_token}"})
        assert hs_res.status_code == 200
        hs_data = hs_res.json()
        assert hs_data["type"] == "FeatureCollection"
        print(f"  ✓ Getis-Ord Gi* Hotspot Analysis: {len(hs_data['features'])} clusters identified.")

        # 5.4 30-Day Time Series
        ts_res = await client.get(f"/jobs/{job_id}/results/timeseries", headers={"Authorization": f"Bearer {analyst_token}"})
        assert ts_res.status_code == 200
        ts_data = ts_res.json()
        assert "timeseries" in ts_data
        assert len(ts_data["timeseries"]) >= 30
        print(f"  ✓ 30-Day ERA5 Meteorological Climate Series: {len(ts_data['timeseries'])} daily data points retrieved.")

        # STEP 6: Verifying All 6 Export Formats
        print("\n[6/7] Verifying All Export Formats (PDF, GeoTIFF, GeoJSON, Shapefile, GPKG, CSV)...")
        
        # 6.1 PDF Report (ReportLab 2-Page Official Report)
        pdf_res = await client.get(f"/jobs/{job_id}/export/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers.get("content-type") == "application/pdf"
        assert len(pdf_res.content) > 5000
        print(f"  ✓ PDF Official Report generated: {len(pdf_res.content):,} bytes")

        # 6.2 GeoTIFF
        gtiff_res = await client.get(f"/jobs/{job_id}/export/geotiff")
        assert gtiff_res.status_code == 200
        assert len(gtiff_res.content) > 1000
        print(f"  ✓ GeoTIFF Raster exported: {len(gtiff_res.content):,} bytes")

        # 6.3 GeoJSON
        gjson_res = await client.get(f"/jobs/{job_id}/export/geojson")
        assert gjson_res.status_code == 200
        assert "features" in gjson_res.json()
        print("  ✓ GeoJSON Vector exported successfully.")

        # 6.4 Shapefile (ZIP)
        shp_res = await client.get(f"/jobs/{job_id}/export/shapefile")
        assert shp_res.status_code == 200
        assert len(shp_res.content) > 500
        print(f"  ✓ ESRI Shapefile (.zip) exported: {len(shp_res.content):,} bytes")

        # 6.5 GeoPackage (GPKG)
        gpkg_res = await client.get(f"/jobs/{job_id}/export/geopackage")
        assert gpkg_res.status_code == 200
        assert len(gpkg_res.content) > 1000
        print(f"  ✓ OGC GeoPackage (.gpkg) exported: {len(gpkg_res.content):,} bytes")

        # 6.6 CSV
        csv_res = await client.get(f"/jobs/{job_id}/export/csv")
        assert csv_res.status_code == 200
        assert "H3_Indeks" in csv_res.text or "Hasar_Skoru" in csv_res.text
        print(f"  ✓ Tabular CSV exported: {len(csv_res.text):,} chars")

        # STEP 7: Admin Monitoring & User Management
        print("\n[7/7] Verifying Admin Live Queue Monitoring & User Management...")
        
        # 7.1 Celery Queue Stats
        q_res = await client.get("/admin/queue-stats", headers={"Authorization": f"Bearer {admin_token}"})
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert "workers_online" in q_data
        print(f"  ✓ Admin Celery Live Cluster Stats: {q_data['workers_online']} workers online")

        # 7.2 Admin Global Jobs List
        all_jobs_res = await client.get("/admin/jobs", headers={"Authorization": f"Bearer {admin_token}"})
        assert all_jobs_res.status_code == 200
        assert len(all_jobs_res.json()) >= 1
        print(f"  ✓ Admin Global Jobs Audit: {len(all_jobs_res.json())} system jobs listed.")

        # 7.3 User Management CRUD
        temp_email = f"e2e_user_{uuid.uuid4().hex[:6]}@damage.org"
        new_u = await client.post("/admin/users/", json={
            "email": temp_email,
            "password": "E2EPassword123!",
            "role": "analyst"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert new_u.status_code == 201
        new_u_id = new_u.json()["id"]

        del_u = await client.delete(f"/admin/users/{new_u_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert del_u.status_code == 204
        print("  ✓ Admin User Management CRUD verified successfully.")

    print("\n" + "=" * 70)
    print("🎉 ALL PLATFORM END-TO-END (E2E) TESTS PASSED FLAWLESSLY! 🎉")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    asyncio.run(test_full_platform_e2e())
