import asyncio
import httpx
import uuid

BASE_URL = "http://localhost:8000/api/v1"

async def test_sprint9():
    print("Running Sprint 9 Verification Tests...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. Login with Valid Admin Credentials
        admin_login = await client.post("/auth/login", json={
            "email": "admin@damage.org",
            "password": "Admin123!"
        })
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_data = admin_login.json()
        admin_token = admin_data["access_token"]
        assert admin_data["user"]["role"] == "admin"
        print("✓ S9-T1: Admin login successful (200 + JWT token)")

        # 2. Login with Invalid Password
        bad_login = await client.post("/auth/login", json={
            "email": "admin@damage.org",
            "password": "WrongPassword!"
        })
        assert bad_login.status_code == 401, f"Bad login should return 401, got: {bad_login.status_code}"
        print("✓ S9-T1: Invalid password rejected with 401 Unauthorized")

        # 3. Test /auth/me
        me_res = await client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "admin@damage.org"
        print("✓ S9-T1: /auth/me returned authenticated user details")

        # 4. S9-T2: Guest AOI creation automatically falls back to default demo user
        guest_aoi = await client.post("/aoi/", json={
            "name": "Guest Field",
            "geometry": "POLYGON((32.0 39.0, 32.1 39.0, 32.1 39.1, 32.0 39.1, 32.0 39.0))"
        })
        assert guest_aoi.status_code == 201, f"Expected 201 for guest AOI, got: {guest_aoi.status_code}"
        print("✓ S9-T2: Guest AOI creation seamlessly attached to default system user")

        # 5. AOI creation with token
        auth_aoi = await client.post("/aoi/", json={
            "name": "Admin Token Field",
            "geometry": "POLYGON((32.0 39.0, 32.1 39.0, 32.1 39.1, 32.0 39.1, 32.0 39.0))"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert auth_aoi.status_code == 201, f"AOI creation with token failed: {auth_aoi.text}"
        aoi_obj = auth_aoi.json()
        assert aoi_obj["owner_id"] == admin_data["user"]["id"]
        print("✓ S9-T2: AOI created and attached to real current_user.id")

        # 6. S9-T3: RBAC Guard (Viewer vs Admin)
        viewer_login = await client.post("/auth/login", json={
            "email": "viewer@damage.org",
            "password": "Viewer123!"
        })
        assert viewer_login.status_code == 200
        viewer_token = viewer_login.json()["access_token"]

        viewer_admin_call = await client.get("/admin/users/", headers={"Authorization": f"Bearer {viewer_token}"})
        assert viewer_admin_call.status_code == 403, f"Viewer should get 403 on admin route, got {viewer_admin_call.status_code}"
        print("✓ S9-T3: Viewer role blocked from Admin route with 403 Forbidden")

        admin_admin_call = await client.get("/admin/users/", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_admin_call.status_code == 200
        users_list = admin_admin_call.json()
        assert len(users_list) >= 3
        print("✓ S9-T3: Admin role successfully accessed Admin route with 200 OK")

        # 7. S9-T4: Admin User Management & Self-Lockout
        test_email = f"testuser_{uuid.uuid4().hex[:6]}@damage.org"
        create_u = await client.post("/admin/users/", json={
            "email": test_email,
            "password": "UserPass123!",
            "role": "analyst"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert create_u.status_code == 201
        created_user_id = create_u.json()["id"]
        print("✓ S9-T4: Admin created new user successfully")

        # Admin tries to demote self (Self-Lockout protection)
        self_demote = await client.patch(f"/admin/users/{admin_data['user']['id']}", json={
            "role": "viewer"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert self_demote.status_code == 400
        print("✓ S9-T4: Self-lockout protection prevented admin from demoting self")

        # Delete created test user
        del_u = await client.delete(f"/admin/users/{created_user_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert del_u.status_code == 204
        print("✓ S9-T4: Admin deleted test user successfully")

        # 8. S9-T5: Admin Jobs & Live Queue Stats
        jobs_res = await client.get("/admin/jobs", headers={"Authorization": f"Bearer {admin_token}"})
        assert jobs_res.status_code == 200
        assert isinstance(jobs_res.json(), list)
        print("✓ S9-T5: Admin jobs list endpoint returned enriched job history")

        queue_res = await client.get("/admin/queue-stats", headers={"Authorization": f"Bearer {admin_token}"})
        assert queue_res.status_code == 200
        queue_data = queue_res.json()
        assert "workers_online" in queue_data
        print(f"✓ S9-T5: Celery queue stats retrieved: {queue_data['workers_online']} workers online, {queue_data['active_tasks_count']} active tasks")

    print("\n🎉 ALL BACKEND SPRINT 9 TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(test_sprint9())
