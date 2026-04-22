
import requests

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
GROUPS_URL = f"{BASE_URL}/api/v1/route-groups/"

def test_delete():
    # 1. Login as admin
    res = requests.post(LOGIN_URL, data={"username": "admin@example.com", "password": "Admin123@Password!"})
    if res.status_code != 200:
        print(f"Login failed: {res.text}")
        return
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. List groups
    res = requests.get(GROUPS_URL, headers=headers)
    groups = res.json()
    print(f"Initial groups: {len(groups)}")
    if not groups:
        print("No groups to delete")
        return
    
    group = groups[0]
    group_id = group["id"]
    print(f"Attempting to delete group: {group['name']} (ID: {group_id})")
    
    # 3. Delete group
    res = requests.delete(f"{GROUPS_URL}{group_id}", headers=headers)
    print(f"Delete response: {res.status_code}")
    
    # 4. Verify
    res = requests.get(GROUPS_URL, headers=headers)
    groups_after = res.json()
    print(f"Groups after delete: {len(groups_after)}")
    
    found = any(g["id"] == group_id for g in groups_after)
    if found:
        print("FAIL: Group still exists after delete")
    else:
        print("SUCCESS: Group was deleted")

if __name__ == "__main__":
    test_delete()
