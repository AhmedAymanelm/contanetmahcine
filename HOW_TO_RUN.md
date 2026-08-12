# How to Run Content Machine

This document outlines the step-by-step process for setting up and running the Content Machine backend API and background services locally.

## Prerequisites

Before you begin, ensure you have the following installed on your system:
* Python 3.10 or higher
* PostgreSQL (or a cloud provider like Neon)
* Playwright (required for backend carousel image rendering)

## 1. Environment Configuration

1. Open a terminal and navigate to the `backend` directory.
2. Create a new `.env` file by duplicating the existing `.env.example` file.
3. Open the `.env` file and configure your essential keys, specifically your `DATABASE_URL` and `ANTHROPIC_API_KEY`. 
Note: While some keys are required here, most social media API keys can also be configured dynamically via the web dashboard.

## 2. Backend Initialization

Navigate to the root directory of the project in your terminal, then execute the following commands in order:

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment to isolate the project dependencies:
   ```bash
   python3 -m venv venv
   ```

3. Activate the virtual environment:
   * On Mac/Linux:
     ```bash
     source venv/bin/activate
     ```
   * On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

5. Install the Playwright dependencies required for generating the visual carousel images:
   ```bash
   playwright install
   playwright install-deps
   ```

6. Run the database migrations to set up your tables in PostgreSQL:
   ```bash
   alembic upgrade head
   ```

## 3. Running the Servers

To start the API server and the automated background workers, run the following command from within the `backend` directory while your virtual environment is active:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

When the FastAPI application starts, the background scheduler (which handles RSS fetching and automated social media publishing) will initialize automatically as part of the application lifespan.

## 4. Accessing the Application

Once the server is running successfully, you can access the interface through your web browser:

* **Dashboard Interface**: Navigate to `http://localhost:8000/` (The backend serves the static frontend files automatically).
* **API Documentation**: Navigate to `http://localhost:8000/docs` to view the interactive Swagger UI and test the API endpoints directly.
