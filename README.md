# Communify Backend API

This is the FastAPI backend server for the Communify AAC application. It handles user authentication, profile management, parental controls, appearance settings, and provides the necessary API endpoints for the frontend application.

**Technologies Used:**

*   **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
*   **Database:** [MongoDB](https://www.mongodb.com/)
*   **ODM (Object-Document Mapper):** [Beanie](https://beanie-odm.dev/) (built on Pydantic and Motor)
*   **Async Driver:** [Motor](https://motor.readthedocs.io/en/stable/)
*   **Data Validation:** [Pydantic](https://docs.pydantic.dev/)
*   **Password Hashing:** [Passlib](https://passlib.readthedocs.io/en/stable/) (with bcrypt)
*   **Authentication:** JWT (JSON Web Tokens) via [python-jose](https://github.com/mpdavis/python-jose/)
*   **Environment Variables:** [python-dotenv](https://github.com/theskumar/python-dotenv) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
*   **Server:** [Uvicorn](https://www.uvicorn.org/)

## Project Structure
communify-backend/
├── app/ # Main application source code
│ ├── api/ # API specific code
│ │ ├── deps.py # Dependency injection (get current user)
│ │ └── v1/ # API Version 1
│ │ ├── api.py # Main v1 API router
│ │ └── endpoints/ # Routers for specific features
│ │ ├── auth.py # Authentication routes
│ │ ├── users.py # User profile routes
│ │ └── settings.py # Parental & Appearance settings routes
│ ├── core/ # Core application logic/config
│ │ ├── config.py # Settings management (env vars)
│ │ └── security.py # Password hashing, JWT handling
│ ├── db/ # Database related code
│ │ ├── database.py # DB connection setup (Beanie init)
│ │ └── models/ # Database models (Beanie Documents)
│ │ ├── enums.py # Shared Enumerations
│ │ ├── user.py
│ │ ├── settings.py # ParentalSettings model
│ │ └── appearance_settings.py # AppearanceSettings model
│ ├── schemas/ # Pydantic schemas for API validation
│ │ ├── token.py
│ │ ├── user.py
│ │ ├── settings.py # ParentalSettings schemas
│ │ └── appearance.py # AppearanceSettings schemas
│ └── main.py # FastAPI app entry point
│
├── .env # Local environment variables (DO NOT COMMIT)
├── .env.example # Example environment file
├── .gitignore # Git ignore rules
├── requirements.txt # Python dependencies
└── README.md # This file


## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd communify-backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Using venv (recommended)
    python -m venv myenv
    # Activate (Linux/macOS)
    source myenv/bin/activate
    # Activate (Windows Git Bash/PowerShell)
    .\myenv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up MongoDB:**
    *   Ensure you have a MongoDB instance running (locally or on a cloud service like MongoDB Atlas).
    *   Obtain the connection string (URI).

5.  **Configure Environment Variables:**
    *   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and fill in your actual values:
        *   `DATABASE_URL`: Your MongoDB connection string (URI). **Remember to replace `<db_password>` with your actual database user password.**
        *   `DATABASE_NAME`: The name of the database to use (e.g., `communify_db` or `Communify`).
        *   `SECRET_KEY`: **Generate a strong, random secret key.** You can use `openssl rand -hex 32` in your terminal to generate one. This is critical for JWT security.
        *   `ALGORITHM`: Keep as `HS256` unless you have specific reasons to change.
        *   `ACCESS_TOKEN_EXPIRE_MINUTES`: Adjust token expiration time if needed (e.g., `60` for one hour).

6.  **(MongoDB Atlas Specific):** Ensure the IP address from which your backend server will run is added to the Network Access list in your Atlas cluster settings.

## Running the Application

1.  **Activate the virtual environment** (if not already active):
    ```bash
    source myenv/bin/activate # Linux/macOS
    # or
    .\myenv\Scripts\activate # Windows
    ```

2.  **Start the development server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    *   `--reload`: Enables auto-reloading when code changes are detected (for development).

3.  The API will be accessible at `http://127.0.0.1:8000`.

## API Documentation

Once the server is running, interactive API documentation (Swagger UI) is available at:

*   `http://127.0.0.1:8000/docs`

Alternative documentation (ReDoc) is available at:

*   `http://127.0.0.1:8000/redoc`

Use the `/docs` interface to test endpoints:
1.  Register a user via `POST /api/v1/auth/register`.
2.  Login via `POST /api/v1/auth/token` using the registered email and password to get an access token.
3.  Click the "Authorize" button (usually top right) and paste the access token in the format `Bearer <your_token>` to authenticate subsequent requests.
4.  Test protected endpoints like `GET /api/v1/users/me` or `PUT /api/v1/settings/parental`.

## Key API Endpoints

*   **Authentication:**
    *   `POST /api/v1/auth/register`: Create a new user account.
    *   `POST /api/v1/auth/token`: Log in and receive a JWT access token.
*   **Users:**
    *   `GET /api/v1/users/me`: Get the profile details of the currently authenticated user.
    *   `PATCH /api/v1/users/me` (Optional): Update profile details (name, avatar).
*   **Settings:**
    *   `GET /api/v1/settings/parental`: Get parental control settings for the current user.
    *   `PUT /api/v1/settings/parental`: Create or update parental control settings.
    *   `GET /api/v1/settings/appearance`: Get appearance/preference settings (TTS, grid, theme, etc.) for the current user.
    *   `PUT /api/v1/settings/appearance`: Create or update appearance/preference settings.


## Database Models

*   **User:** Stores core user information (email, name, hashed password, profile details).
*   **ParentalSettings:** Stores parental control configurations linked to a user.
*   **AppearanceSettings:** Stores user preferences for UI and interaction (grid layout, font size, theme, TTS settings, selection mode) linked to a user.

*(Note: Custom Symbols and Categories are currently managed locally on the frontend via AsyncStorage)*
