"""
Tests for Banner Access Tracker
Run with: pytest
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User, Role, AccessRequest, Approval, Form, PermissionGroup
from app.utils.auth import hash_password

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create roles
    grantee_role = Role(id=1, name="Grantee")
    grantor_role = Role(id=2, name="Grantor")
    admin_role = Role(id=3, name="Administrator")
    db.add_all([grantee_role, grantor_role, admin_role])
    
    # Create test users
    grantee = User(id=1, cwid="10000001", username="grantee1", password_hash=hash_password("password"), role_id=1)
    grantor1 = User(id=2, cwid="20000001", username="grantor1", password_hash=hash_password("password"), role_id=2)
    grantor2 = User(id=3, cwid="20000002", username="grantor2", password_hash=hash_password("password"), role_id=2)
    admin = User(id=4, cwid="30000001", username="admin1", password_hash=hash_password("password"), role_id=3)
    db.add_all([grantee, grantor1, grantor2, admin])
    
    # Create test forms and permission groups
    form1 = Form(id=1, code="TEST01", description="Test Form 1", active=True)
    perm1 = PermissionGroup(id=1, name="Test Permission", description="Test", active=True)
    db.add_all([form1, perm1])
    
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    """Create test client"""
    return TestClient(app)


def test_login_success(client, test_db):
    """Test successful login"""
    response = client.post("/login", data={"username": "grantee1", "password": "password"})
    assert response.status_code == 303
    assert response.cookies.get("banner_session") is not None


def test_login_failure(client, test_db):
    """Test failed login with wrong password"""
    response = client.post("/login", data={"username": "grantee1", "password": "wrongpassword"})
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_dual_approval_workflow(client, test_db):
    """Test dual approval requirement"""
    # Login as grantee and create request
    client.post("/login", data={"username": "grantee1", "password": "password"})
    
    # Create access request
    request = AccessRequest(
        id=1,
        applicant_user_id=1,
        submitted_by_user_id=1,
        status="Pending"
    )
    test_db.add(request)
    test_db.commit()
    
    # First approval by grantor1
    client.get("/logout")
    client.post("/login", data={"username": "grantor1", "password": "password"})
    response = client.post("/grantor/requests/1/approve", data={"comment": "Approved"})
    assert response.status_code == 303
    
    # Check request still pending (needs 2 approvals)
    test_db.refresh(request)
    assert request.status == "Pending"
    
    # Check only 1 approval exists
    approvals = test_db.query(Approval).filter(Approval.access_request_id == 1).all()
    assert len(approvals) == 1
    
    # Second approval by grantor2
    client.get("/logout")
    client.post("/login", data={"username": "grantor2", "password": "password"})
    response = client.post("/grantor/requests/1/approve", data={"comment": "Approved"})
    assert response.status_code == 303
    
    # Check request now approved
    test_db.refresh(request)
    assert request.status == "Approved"
    
    # Check 2 approvals exist
    approvals = test_db.query(Approval).filter(Approval.access_request_id == 1).all()
    assert len(approvals) == 2


def test_same_grantor_cannot_approve_twice(client, test_db):
    """Test that same grantor cannot approve twice"""
    # Create access request
    request = AccessRequest(
        id=2,
        applicant_user_id=1,
        submitted_by_user_id=1,
        status="Pending"
    )
    test_db.add(request)
    test_db.commit()
    
    # Login as grantor1
    client.post("/login", data={"username": "grantor1", "password": "password"})
    
    # First approval
    response = client.post("/grantor/requests/2/approve", data={"comment": "Approved"})
    assert response.status_code == 303
    
    # Try to approve again
    response = client.post("/grantor/requests/2/approve", data={"comment": "Approved again"})
    assert response.status_code == 303
    assert "already_reviewed" in response.headers.get("location", "")
    
    # Check only 1 approval exists
    approvals = test_db.query(Approval).filter(Approval.access_request_id == 2).all()
    assert len(approvals) == 1


def test_denial_stops_approval_process(client, test_db):
    """Test that denial immediately rejects the request"""
    # Create access request
    request = AccessRequest(
        id=3,
        applicant_user_id=1,
        submitted_by_user_id=1,
        status="Pending"
    )
    test_db.add(request)
    test_db.commit()
    
    # Login as grantor1 and deny
    client.post("/login", data={"username": "grantor1", "password": "password"})
    response = client.post("/grantor/requests/3/deny", data={"comment": "Not appropriate"})
    assert response.status_code == 303
    
    # Check request is rejected
    test_db.refresh(request)
    assert request.status == "Rejected"


def test_admin_can_update_status(client, test_db):
    """Test admin can update request status"""
    # Create access request
    request = AccessRequest(
        id=4,
        applicant_user_id=1,
        submitted_by_user_id=1,
        status="Pending"
    )
    test_db.add(request)
    test_db.commit()
    
    # Login as admin
    client.post("/login", data={"username": "admin1", "password": "password"})
    
    # Update status
    response = client.post("/admin/requests/4/status", data={"new_status": "In Progress"})
    assert response.status_code == 303
    
    # Check status updated
    test_db.refresh(request)
    assert request.status == "In Progress"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
