# Stage 1: Build the Vue.js frontend
FROM node:24 AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build


FROM fedora:43 AS production

# Install system dependencies required by WeasyPrint
RUN dnf install -y weasyprint python-pip

## Install WeasyPrint
#RUN pip install --no-cache-dir weasyprint


# Stage 2: Build the Django backend
FROM production

ENV UV_NO_DEV=1
ENV SECRET_KEY=123
ENV JWT_SECRET_KEY=12345

ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_EMAIL=admin@gmail.com
ENV DJANGO_SUPERUSER_PASSWORD=admin


WORKDIR /app

# Install uv
RUN pip install uv

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync

# Copy the rest of the backend code
COPY . .

# Copy the built frontend from the builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

RUN uv run manage.py migrate
RUN uv run manage.py collectstatic
RUN uv run manage.py createsuperuser --noinput

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uv", "run", "python", "-m", "gunicorn", "--bind", "0.0.0.0:8000", "conf.wsgi:application"]
