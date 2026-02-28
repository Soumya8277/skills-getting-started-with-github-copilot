"""
Test suite for Mergington High School Activity Management API

Tests all endpoints including:
- GET / (redirect to index)
- GET /activities (retrieve all activities)
- POST /activities/{activity_name}/signup (student registration)
- DELETE /activities/{activity_name}/signup (student unregistration)
"""

import pytest
from copy import deepcopy
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a TestClient instance for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before and after each test"""
    # Store the initial state
    initial_state = deepcopy(activities)
    yield
    # Restore state after test
    activities.clear()
    activities.update(initial_state)


class TestRootEndpoint:
    """Test the root endpoint redirect"""
    
    def test_root_redirects_to_index(self, client):
        """GET / should redirect to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """GET /activities should return all activities with correct structure"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify we have 9 activities
        assert len(data) == 9
        
        # Verify all expected activities are present
        expected_activities = {
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Drama Club",
            "Art Gallery",
            "Debate Team",
            "Science Club"
        }
        assert set(data.keys()) == expected_activities
    
    def test_get_activities_contains_required_fields(self, client, reset_activities):
        """Each activity should have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = {"description", "schedule", "max_participants", "participants"}
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_data, dict), f"{activity_name} is not a dict"
            assert set(activity_data.keys()) == required_fields, \
                f"{activity_name} missing required fields"
    
    def test_get_activities_participants_are_lists(self, client, reset_activities):
        """Participants field should be a list for each activity"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_data["participants"], list), \
                f"{activity_name} participants is not a list"


class TestSignup:
    """Test the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Successfully sign up a new student"""
        email = "newstudent@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify student was added
        assert email in activities[activity]["participants"]
    
    def test_signup_adds_student_to_participants(self, client, reset_activities):
        """Verify signup actually adds the email to participants list"""
        email = "test@mergington.edu"
        activity = "Programming Class"
        
        initial_count = len(activities[activity]["participants"])
        
        client.post(f"/activities/{activity}/signup", params={"email": email})
        
        new_count = len(activities[activity]["participants"])
        assert new_count == initial_count + 1
        assert email in activities[activity]["participants"]
    
    def test_signup_duplicate_email_returns_error(self, client, reset_activities):
        """Attempting to sign up with an existing email should fail"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity = "Chess Club"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Attempting to sign up for non-existent activity should fail"""
        email = "test@mergington.edu"
        activity = "Nonexistent Activity"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_students_same_activity(self, client, reset_activities):
        """Multiple different students should be able to sign up"""
        activity = "Tennis Club"
        emails = ["alice@mergington.edu", "bob@mergington.edu", "charlie@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were added
        for email in emails:
            assert email in activities[activity]["participants"]
    
    def test_signup_same_student_different_activities(self, client, reset_activities):
        """Same student can sign up for multiple different activities"""
        email = "uniquestudent@mergington.edu"
        activities_to_join = ["Chess Club", "Drama Club", "Science Club"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        for activity in activities_to_join:
            assert email in activities[activity]["participants"]


class TestUnregister:
    """Test the DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Successfully unregister an enrolled student"""
        email = "michael@mergington.edu"  # Enrolled in Chess Club
        activity = "Chess Club"
        
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify student was removed
        assert email not in activities[activity]["participants"]
    
    def test_unregister_removes_from_participants(self, client, reset_activities):
        """Verify unregister actually removes the email from participants list"""
        email = "emma@mergington.edu"  # Enrolled in Programming Class
        activity = "Programming Class"
        
        initial_count = len(activities[activity]["participants"])
        assert email in activities[activity]["participants"]
        
        client.delete(f"/activities/{activity}/signup", params={"email": email})
        
        new_count = len(activities[activity]["participants"])
        assert new_count == initial_count - 1
        assert email not in activities[activity]["participants"]
    
    def test_unregister_not_enrolled_returns_error(self, client, reset_activities):
        """Attempting to unregister a non-enrolled student should fail"""
        email = "notenrolled@mergington.edu"
        activity = "Chess Club"
        
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Attempting to unregister from non-existent activity should fail"""
        email = "test@mergington.edu"
        activity = "Nonexistent Activity"
        
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_then_reenroll(self, client, reset_activities):
        """A student should be able to re-enroll after unregistering"""
        email = "testuser@mergington.edu"
        activity = "Debate Team"
        
        # Initial signup
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Unregister
        response2 = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Re-register
        response3 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        assert email in activities[activity]["participants"]


class TestIntegration:
    """Integration tests for combined operations"""
    
    def test_signup_and_unregister_flow(self, client, reset_activities):
        """Test complete signup and unregister workflow"""
        email = "integrationtest@mergington.edu"
        activity = "Art Gallery"
        
        # Verify student not initially enrolled
        assert email not in activities[activity]["participants"]
        
        # Sign up
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Get activities to verify listed
        response2 = client.get("/activities")
        assert email in response2.json()[activity]["participants"]
        
        # Unregister
        response3 = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Verify removal via get activities
        response4 = client.get("/activities")
        assert email not in response4.json()[activity]["participants"]
    
    def test_multiple_students_independent_state(self, client, reset_activities):
        """Verify state changes for one student don't affect others"""
        activity = "Gym Class"
        student1 = "student1@mergington.edu"
        student2 = "student2@mergington.edu"
        already_enrolled = "john@mergington.edu"  # Already in Gym Class
        
        # Sign up student 1
        client.post(f"/activities/{activity}/signup", params={"email": student1})
        
        # Sign up student 2
        client.post(f"/activities/{activity}/signup", params={"email": student2})
        
        # Unregister student 1
        client.delete(f"/activities/{activity}/signup", params={"email": student1})
        
        # Verify only student 1 was removed, others remain
        current = activities[activity]["participants"]
        assert student1 not in current
        assert student2 in current
        assert already_enrolled in current
