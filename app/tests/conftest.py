import os
if test_url := os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = test_url
