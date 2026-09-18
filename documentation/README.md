# Project Documentation (`documentation/`)

## 1. Overview
The `documentation/` directory contains system architecture specifications, data source dictionaries, API contracts, and guides for the **NER Safe** platform.

## 2. Directory Contents

| Document | Topic | Description |
| :--- | :--- | :--- |
| `architecture.md` | System Architecture | Detailed overview of the monolithic FastAPI backend, PostGIS spatial layer, React frontend, and ML inference flow. |
| `data_sources.md` | Data Registry & Provenance | Complete list of official government and satellite data portals (GSI, IMD, Bhuvan, Copernicus, NASA), license types, and update frequencies. |
| `api_specification.md`| API Documentation | Endpoint specifications, query parameters, request/response bodies, and status codes for public and administrative endpoints. |
| `pilot_districts.md` | Geographic Profile | Topographical, geological, and meteorological profiles of Kohima District (Nagaland) and Aizawl District (Mizoram). |
| `setup_guide.md` | Developer Setup | Instructions for local installation, setting up PostgreSQL + PostGIS, Python virtual environments, and Node dependencies. |

## 3. Maintenance Guidelines
- Keep documentation synchronized with actual code and schema changes.
- Clearly differentiate implemented capabilities from planned features.
