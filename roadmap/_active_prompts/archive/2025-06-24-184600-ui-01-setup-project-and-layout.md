# Task: UI Rebuild - Project Setup and Layout

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Initialize a new, clean `biomapper-ui` project using Vite, React, and TypeScript. Set up the basic project structure, install essential dependencies, and create the main application shell layout using Mantine.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** None for this task.
- **Service Dependencies:** This task is foundational and has no service dependencies, but the created UI will eventually depend on `biomapper-api`.

## 3. Prerequisites
- [ ] `npm` (or `yarn`/`pnpm`) is installed.
- [ ] The old `/home/ubuntu/biomapper/biomapper-ui` directory should be backed up or removed to allow for a clean setup.

## 4. Task Decomposition
1.  **Initialize Project:** Create a new Vite project with the `react-ts` template in `/home/ubuntu/biomapper/biomapper-ui`.
2.  **Install Dependencies:** Add Mantine for UI components, Tabler Icons, and Axios for future API calls.
3.  **Configure Mantine:** Set up the Mantine provider in `main.tsx`.
4.  **Create App Layout:** In `App.tsx`, implement a Mantine `AppShell` with a header and a sidebar for navigation. This will serve as the main layout for the application.
5.  **Add Basic Styling:** Create a basic `index.css` file for global styles.

## 5. Implementation Requirements
- **Project Root:** `/home/ubuntu/biomapper/biomapper-ui`
- **Command to initialize project:** `npm create vite@latest . -- --template react-ts`
- **Dependencies to install:** `@mantine/core @mantine/hooks @emotion/react @tabler/icons-react axios`
- **`App.tsx`:** Should contain the `AppShell` with a `Header` and `Navbar`. The navbar should contain placeholder `NavLink` items for the workflow steps (Upload, Columns, Mapping, Results).
- **`main.tsx`:** Should wrap the `<App />` component with `<MantineProvider>`.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The new Vite project is created at `/home/ubuntu/biomapper/biomapper-ui`.
- [ ] All specified dependencies are listed in `package.json`.
- [ ] Running `npm install` and `npm run dev` successfully starts the development server.
- [ ] The browser shows the basic Mantine `AppShell` layout with a header and sidebar.
