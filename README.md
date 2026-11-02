# Smart Tutor

Smart Tutor is a source-code showcase organized by development stages.

The project supports submitting problem images, solving math and physics problems, step-by-step guidance, OCR, knowledge lookup, and security and red-team testing. It also includes a unified math/physics web portal and gateway.

## Project Structure

- `smart_tutor/`: The problem-solving service, including the web interface, image-recognition integration, solution logic, physics knowledge base, step-by-step guidance, answer verification, security protections, and red-team testing endpoints.
- `portal/`: The unified math/physics web portal, session login, and API gateway.

The modules retain their respective service interfaces and dependency configurations. The portal forwards requests to local backend services. Deployment requires configuring the backend addresses, dependencies, and runtime environment for the relevant services.

The project also contains a large collection of attack-test samples, which are not being uploaded due to privacy concerns. The problem-image dataset, original problem/solution/answer images, textbook materials, and user data are not included in this repository.

## Features

- Submit problem images for math or physics solutions
- Full solutions and step-by-step guidance
- OCR, knowledge expansion, error tracking, and study-support features
- Input safety checks, output filtering, and red-team testing endpoints
- Unified math/physics web portal and authenticated gateway

This repository showcases source code. Model services, OCR environments, third-party dependencies, and deployment settings must be prepared for the target runtime environment.
