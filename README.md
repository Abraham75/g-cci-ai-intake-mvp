# G-CCI AI Intake MVP

## Overview
This project serves as a Minimum Viable Product (MVP) for the G-CCI AI Intake system, designed to streamline and enhance the process of AI data intake.

## Features
- **Server-side logic**: Handles functionalities like scoring, explaining decisions, compliance checks, alerts, and more.
- **Frontend Interface**: Basic web UI to display and interact with data inputs and outputs.

## File Structure
```
project/
|-- server/
|   |-- index.js
|   |-- models.js
|   |-- scoring.js
|   |-- explain.js
|   |-- compliance.js
|   |-- alerts.js
|   |-- store.js
|-- public/
|   |-- index.html
|   |-- app.js
|   |-- styles.css
|-- .gitignore
|-- package.json
|-- README.md
```

## Requirements
- **Node.js**: v14 or later is recommended.
- **Dependencies**:
  - express
  - ws
  - uuid
  - cors

## Setup
1. Clone the repository.
```bash
git clone https://github.com/Abraham75/g-cci-ai-intake-mvp.git
```
2. Install dependencies.
```bash
npm install
```
3. Start the application.
```bash
npm start
```

## License
This project is licensed under the MIT License. See `LICENSE` for details.

---

**Created by Abraham75**.