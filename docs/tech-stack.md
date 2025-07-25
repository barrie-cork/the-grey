# Technology Stack for Thesis Grey

This document outlines the technology stack for the Thesis Grey project, as derived from the [Project Requirements Document (PRD)](PRD.md:0) and further research.

## Core Technologies (Phase 1)

- **Framework:** Django `4.2.x` (Python)
    - **Rationale and Considerations:**
        - **Suitability for Thesis Grey:** Django's "batteries-included" philosophy is ideal for "Thesis Grey," offering a powerful ORM for managing complex research data (search sessions, results, user accounts), a built-in admin panel for easy data oversight and management by administrators, and robust security features (CSRF, XSS protection) crucial for protecting user data and research integrity. Its structured nature facilitates rapid development of data-intensive applications.
        - **Version Specifics (4.2.x):** As a Long-Term Support (LTS) release (supported until April 2026), Django 4.2.x provides stability, extended security updates, and bug fixes, making it a reliable choice for a new project. It includes native support for `Psycopg 3` (for PostgreSQL), asynchronous ORM operations (beta in 4.2, potentially useful for future scaling), and various other improvements over older versions.
        - **Alternatives:**
            - **Flask/FastAPI:** While excellent for microservices or API-centric applications (FastAPI for high performance), they require more manual setup and integration of components like ORMs, admin interfaces, and form handling, which Django provides out-of-the-box. For a full-featured application like Thesis Grey, Django's integrated components typically lead to faster initial development and less boilerplate.
            - **Older Django Versions:** Using the latest LTS (4.2.x) ensures access to the most recent features, security patches, and a longer support window, which is preferable to starting a new project on an older or non-LTS version.

- **Frontend:** Django Templates, HTML, CSS (with TailwindCSS), JavaScript (for AJAX interactivity)
    - **Rationale and Considerations:**
        - **Suitability for Thesis Grey (Phase 1):** For Phase 1, focusing on core functionality and rapid development, Django's built-in template system is highly efficient. It allows for tight integration with the Django backend, reducing complexity and development time for server-rendered pages. This is well-suited for data-driven interfaces where complex client-side state management is not an immediate primary concern.
        - **HTML/CSS/JavaScript:** Standard web technologies provide the necessary tools for structuring content (HTML), styling (CSS), and adding client-side interactivity (JavaScript, e.g., for AJAX form submissions, dynamic updates to parts of a page without full reloads).
        - **TailwindCSS:** TailwindCSS will be used to speed up UI development by providing utility classes, allowing for rapid styling directly in the HTML. This provides a consistent look and feel quickly without requiring a dedicated frontend designer.
        - **Alternatives (JS Frameworks like React/Vue):**
            - While powerful for building highly interactive Single Page Applications (SPAs), introducing a full JavaScript framework in Phase 1 adds complexity (separate build processes, API development for Django, state management).
            - For the initial goals of Thesis Grey, the benefits of an SPA might not outweigh the increased development overhead. Django templates offer a simpler, more direct path to delivering core features quickly. A JS framework could be considered for Phase 2 if more complex client-side interactivity becomes a primary requirement.

- **Backend:** Django, Django ORM
    - **Rationale and Considerations:**
        - **Integrated Solution:** Since Django is the chosen framework, its own backend components, including the ORM, are inherently the most integrated and natural choice. This ensures seamless operation between the request-response cycle, business logic, and data persistence.
        - **Django ORM Benefits for Thesis Grey:**
            - **Data Modeling:** The ORM allows defining complex database schemas (like those for `SearchSession`, `ProcessedResult`, `User`, etc.) directly in Python code, making it intuitive and maintainable.
            - **Migrations:** Django's built-in migration system automates schema changes, tracking them in version-controlled files, which is crucial for evolving the database structure as Thesis Grey develops.
            - **Querying:** Provides a high-level, Pythonic API for database queries, abstracting away much of the raw SQL. This speeds up development and can improve security (e.g., by mitigating SQL injection risks). For Thesis Grey, this means easier querying of research data, filtering results, and managing relationships between entities.
            - **Database Agnosticism (to a degree):** While PostgreSQL is specified, the ORM provides a layer that can simplify switching databases if ever needed, though advanced database-specific features might require direct SQL.
        - **Performance & Best Practices:**
            - While highly convenient, complex ORM queries can sometimes lead to inefficient database calls if not carefully constructed.
            - **Best Practices for Thesis Grey:** Use `select_related` and `prefetch_related` to optimize queries involving foreign key and many-to-many relationships, reducing the number of database hits. Utilize Django Debug Toolbar during development to inspect queries. For very complex reporting or data aggregation, consider raw SQL or database views if ORM queries become a bottleneck. Index database fields that are frequently queried or used in `WHERE` clauses.

- **Database:** PostgreSQL (using Psycopg 3)
    - **Rationale and Considerations:**
        - **Suitability of PostgreSQL for Thesis Grey:**
            - **Robustness & Reliability:** PostgreSQL is renowned for its data integrity, ACID compliance, and robustness, making it suitable for storing valuable research data where consistency is paramount.
            - **Scalability & Performance:** It handles complex queries and large datasets well, which is important as Thesis Grey accumulates search results and user data.
            - **Advanced Features:** Offers a rich feature set, including support for JSONB (efficiently storing and querying JSON data, potentially useful for `RawSearchResult`), full-text search capabilities (could enhance searching within collected snippets or notes in future phases), and extensibility (e.g., PostGIS for geospatial data, though not immediately relevant for Phase 1).
            - **Django Integration:** PostgreSQL is a first-class citizen in the Django world, with excellent ORM support.
        - **Psycopg 3 Adapter:**
            - **Modern & Performant:** Psycopg 3 is the latest generation adapter for connecting Python to PostgreSQL. It offers improved performance, better type handling (especially for modern Python features like type hints), and more efficient use of server-side features compared to Psycopg 2.
            - **Django 4.2+ Recommendation:** Django 4.2 and later versions have improved native support and recommend Psycopg 3 for new projects due to its modern features and ongoing development focus.
        - **Alternatives:**
            - **MySQL/MariaDB:** While capable, PostgreSQL is often favored for applications requiring complex queries, high data integrity, and advanced data types.
            - **SQLite:** Suitable for development and very small applications, but not recommended for production environments like Thesis Grey due to limitations in concurrency and scalability.

- **APIs (External):** Google Search API via Serper (using a Python client like `requests`)
    - **Rationale and Considerations:**
        - **Serper API Benefits:**
            - **Simplified Access:** Serper often provides a more straightforward and potentially more cost-effective way to access Google Search results for specific use cases compared to navigating the complexities and quota systems of Google's official Custom Search JSON API. It typically offers a flat-rate pricing model or clear per-query costs.
            - **Ease of Integration:** Designed for developers, Serper's API is generally easy to integrate, returning structured JSON data that can be readily parsed by a Python client.
        - **Python `requests` Client:**
            - **Simplicity & Ubiquity:** The `requests` library is the de facto standard for making HTTP requests in Python due to its simple API and robustness. It's well-suited for interacting with Serper's RESTful API.
        - **Key Considerations for Thesis Grey:**
            - **API Key Management:** API keys for Serper must be stored securely (e.g., using environment variables or Django's settings loaded from a secure source, never hardcoded in version control).
            - **Rate Limiting:** Be mindful of Serper's API rate limits. Implement appropriate delays or queuing mechanisms within Celery tasks if making many requests in a short period to avoid being blocked.
            - **Error Handling:** The `requests` client code should robustly handle potential HTTP errors (e.g., 4xx, 5xx status codes), network issues, and timeouts. Implement retries with backoff strategies for transient errors within Celery tasks.
            - **Data Parsing:** Ensure the client code correctly parses the JSON response from Serper to extract relevant fields (URL, title, snippet) for `RawSearchResult`.
        - **Alternative (Google Custom Search JSON API):** While official, it can be more complex to set up and manage, especially regarding quotas and billing for high-volume usage. Serper often acts as a more developer-friendly layer on top.

- **Background Tasks:** Celery with Redis as the message broker
    - **Rationale and Considerations:**
        - **Why Celery for Thesis Grey:**
            - **Asynchronous Processing:** Essential for offloading long-running tasks like external API calls (to Serper) and data processing (normalizing results, deduplication) from the main web request-response cycle. This prevents users from experiencing long waits or timeouts.
            - **Django Integration:** Celery has excellent integration with Django, making it straightforward to define and trigger tasks from Django views or signals.
            - **Scalability:** Celery workers can be scaled independently to handle varying task loads.
            - **Features:** Supports task scheduling (Celery Beat), retries, rate limiting, and more, which are valuable for robust background processing.
        - **Broker Choice (Redis vs. RabbitMQ):**
            - **Redis:**
                - *Pros:* Very fast, lightweight, simple to set up and manage. Often used for caching as well, so it might already be in the stack. Good for simpler task queuing needs and when high message persistence isn't the absolute top priority (though it offers configurable persistence).
                - *Cons:* Less feature-rich in terms of complex routing and message guarantees compared to RabbitMQ. If a Redis server crashes before data is persisted to disk (if configured), tasks could be lost.
            - **RabbitMQ:**
                - *Pros:* A dedicated, robust message broker with more advanced features like flexible routing, message acknowledgments, and better guarantees for message persistence and delivery. Generally preferred for critical tasks where losing a message is unacceptable.
                - *Cons:* More complex to set up and manage than Redis. Higher resource footprint.
            - **Recommendation for Thesis Grey (Phase 1):** **Redis** will be used as it is sufficient and simpler to manage for Phase 1 requirements. Tasks will be designed to be idempotent to handle potential failures gracefully.
        - **Celery Best Practices for Thesis Grey:**
            - **Idempotent Tasks:** Design tasks to be idempotent where possible (running them multiple times has the same effect as running once) to handle retries safely.
            - **Task Granularity:** Keep tasks relatively small and focused on a single unit of work.
            - **Error Handling:** Implement robust error handling within tasks, including logging and appropriate retry mechanisms (e.g., `autoretry_for`, `retry_backoff`).
            - **Monitoring:** Use tools like Flower to monitor Celery tasks and workers.
            - **Result Backend:** Configure a result backend (e.g., Django database backend, Redis) if task results need to be stored and retrieved.

- **DevOps:** Docker, GitHub Actions (basic CI/CD)
    - **Rationale and Considerations:**
        - **Docker for Thesis Grey:**
            - **Development Consistency:** Docker ensures that all developers work in an identical environment, mirroring the production setup. This eliminates "works on my machine" issues by containerizing the Django app, PostgreSQL, Redis/RabbitMQ, and Celery workers.
            - **Simplified Setup:** New developers can quickly get started with a `docker-compose up` command.
            - **Deployment Portability:** Docker containers can be deployed consistently across various environments (local, staging, production).
            - **Isolation:** Services run in isolated containers, improving security and stability.
            - **Dockerfile & `docker-compose.yml`:**
                - A `Dockerfile` will define the image for the Django application (including Python dependencies, application code, and Gunicorn/Uvicorn).
                - A `docker-compose.yml` will define and orchestrate all services: the Django app, Celery worker(s), Celery Beat (if used), PostgreSQL database, and Redis/RabbitMQ broker. It will manage networking between containers and volume mounts for persistent data (e.g., database files) and code.
        - **GitHub Actions (Basic CI/CD for Phase 1):**
            - **Automation:** Automates repetitive tasks triggered by code pushes or pull requests.
            - **Continuous Integration (CI):**
                - **Linting:** Automatically run linters (e.g., Flake8, Black) to enforce code style.
                - **Testing:** Automatically run the Django test suite (`python manage.py test`) to catch regressions early.
            - **Continuous Delivery/Deployment (CD - Basic):**
                - **Build Docker Images:** Optionally, build Docker images upon successful tests on the main branch and push them to a container registry (e.g., Docker Hub, GitHub Container Registry).
                - Actual deployment to a server might be manual in Phase 1 after CI passes, but the groundwork for automated deployment can be laid.
        - **Benefits for Thesis Grey:** This setup promotes a more reliable development process, catches errors earlier, and simplifies both local development and the path to deployment.

- **API Development (Internal - Optional for Phase 1, core for Phase 2):** Django REST Framework
    - **Rationale and Considerations:**
        - **Why DRF for Thesis Grey (Phase 2):**
            - **Standard for Django APIs:** DRF is the most widely adopted and comprehensive toolkit for building Web APIs with Django. It provides a rich set of features that significantly speed up API development.
            - **Decoupled Frontend:** If Phase 2 involves a more complex, JavaScript-based frontend (e.g., React, Vue, Angular), DRF would provide the necessary API endpoints for the frontend to consume and interact with data.
            - **Third-Party Integrations:** If Thesis Grey needs to expose its data or functionality to other services or allow external tools to interact with it, a well-defined REST API built with DRF is essential.
            - **Mobile Applications:** Should mobile access be a future requirement, DRF would serve as the backend.
        - **Key DRF Components and Their Use in Thesis Grey:**
            - **Serializers:** Convert complex data types, such as Django model instances, into native Python datatypes that can then be easily rendered into JSON, XML, or other content types. They also handle deserialization and validation of incoming data. For Thesis Grey, serializers would be defined for models like `SearchSession`, `ProcessedResult`, etc.
            - **ViewSets:** Provide a higher-level abstraction for handling the logic of API endpoints. They can automatically create CRUD (Create, Read, Update, Delete) operations for models with minimal code, often by combining logic for multiple related views into a single class.
            - **Routers:** Work with ViewSets to automatically generate URL patterns for your API, further reducing boilerplate code.
            - **Authentication & Permissions:** DRF integrates with Django's authentication system and provides flexible permission classes to control access to API endpoints.
        - **Phase 1 Consideration:** While not core for Phase 1 if using Django templates for the frontend, designing models and business logic with future API exposure in mind (e.g., clear service layers) can make the transition to DRF in Phase 2 smoother. Basic API needs in Phase 1 (if any, e.g., for AJAX calls) could potentially be handled with simple Django JSON responses, deferring full DRF adoption.