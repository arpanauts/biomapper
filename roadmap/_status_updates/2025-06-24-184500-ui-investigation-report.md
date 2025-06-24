# Biomapper UI Investigation Report

**Date:** 2025-06-24

## 1. Executive Summary

This report details the findings of an investigation into the current state of the `biomapper-ui`. The primary recommendation is to **rebuild the user interface from scratch**. The most critical issue uncovered is the absence of a `package.json` file, which makes it impossible to reliably determine and install the project's dependencies. A rebuild will provide a stable, modern, and maintainable foundation for the UI, designed from the outset to integrate with the `biomapper-api`.

## 2. Investigation Findings

### 2.1. Technology Stack

-   **Framework:** The UI is a React application.
-   **Build Tool:** It uses Vite for development and bundling.
-   **UI Components:** The project utilizes the Mantine component library.
-   **Language:** The components are written in TypeScript (`.tsx`).

### 2.2. Critical Issues

-   **Missing `package.json`:** This is the most significant problem. Without this file, there is no definitive list of project dependencies and their versions. This makes it impossible to create a reproducible build or to reliably add new dependencies.

### 2.3. Existing Structure and Logic

-   **Application Workflow:** The `src/App.tsx` file outlines a clear, multi-step user workflow:
    1.  File Upload
    2.  Column Selection
    3.  Mapping Configuration
    4.  Results Viewing
-   **Component-Based Architecture:** The application is structured with reusable components for each step of the workflow, located in the `src/components` directory.
-   **API Proxy:** The `vite.config.ts` file is correctly configured to proxy API requests to the `biomapper-api` service at `http://localhost:8000`.

## 3. Recommendation: Rebuild from Scratch

I strongly recommend rebuilding the `biomapper-ui` rather than attempting to refactor the existing, broken project.

### 3.1. Justification

-   **Reproducibility and Stability:** A new project with a properly managed `package.json` will ensure that the development environment is stable and reproducible.
-   **Modern Foundation:** A rebuild allows for the use of the latest, stable versions of React, Vite, and other libraries, which will improve performance, security, and developer experience.
-   **API-First Design:** The new UI can be designed with the `biomapper-api` as its primary data source from the beginning, leading to a cleaner and more robust integration.
-   **Reduced Technical Debt:** Attempting to reverse-engineer the missing dependencies would be time-consuming and would likely result in a fragile and difficult-to-maintain application. Starting fresh avoids this technical debt.

### 3.2. Next Steps

1.  **Initialize a new React project** using Vite and TypeScript.
2.  **Add core dependencies:** `react`, `react-dom`, `@mantine/core`, `@tabler/icons-react`, and `axios` (or a similar HTTP client).
3.  **Re-implement the UI components** based on the logic in the existing `src` directory, connecting them to the `biomapper-api` instead of mock data or local state where appropriate.
4.  **Establish a clear project structure** with documentation for future development.
