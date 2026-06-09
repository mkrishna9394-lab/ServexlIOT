# Industrial IoT Cloud Platform

Modular end-to-end FastAPI web application based on the uploaded requirement PDF.

## Features included
- Login/logout with role-based pages
- Super Admin and Customer dashboards
- Customer -> Site -> Gateway -> Sensor -> Tag hierarchy
- MQTT ingestion worker with reconnect handling
- Live data cache and historical logging
- Trends, reports, alerts, audit logs, diagnostics, settings
- Responsive industrial UI
- SQLite default for quick testing; MariaDB/PostgreSQL supported through `DATABASE_URL`

## Quick start on Windows CMD
```bat
cd iiot_cloud_platform
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python create_admin.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open: http://127.0.0.1:8000

Default login after `create_admin.py`:
- Email: admin@example.com
- Password: Admin@123

## MariaDB connection example
Update `.env`:
```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/iiot_cloud
```
Create database first:
```sql
CREATE DATABASE iiot_cloud CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## MQTT payload format
Topic example:
```text
customers/1/sites/1/gateways/GW001/sensors/SN001/data
```
Payload example:
```json
{"temperature": 32.5, "pressure": 5.8, "production_count": 120, "oee": 78.5}
```
Configure tag keys in the UI or seed data.
