# StrokeVision - Project Presentation

## Slide 1: Title Slide
**Title:** StrokeVision: Decision Support System for Early Stroke Detection
**Subtitle:** A Secure, AI-Driven Clinical Web Application
**Presenter:** [Your Name]
**Duration:** 30 seconds

**Speaker Notes:**
- Welcome everyone. I am here to present **StrokeVision**, a web-based decision support system designed researchers and healthcare professionals.
- The project integrates **Clinical Data Management** with **Deep Learning** to predict stroke risk.
- My focus today is on the **Secure Software Development Life Cycle (SSDLC)**, demonstrating how security, privacy, and professional practices were embedded from design to deployment.

---

## Slide 2: Project Overview & Objectives
**Title:** System Overview
**Content:**
- **Goal:** Early detection of stroke risk using ML on patient vitals.
- **Key Features:**
  - Role-Based Access Control (RBAC) (Admin/Doctor/Nurse).
  - Secure CRUD for Patient Records.
  - Real-time Risk Prediction (Keras/TensorFlow).
  - Data Privacy Compliance (GDPR/NHS).
- **Target Users:** Medical Professionals (Doctors/Nurses) & Administrators.

**Speaker Notes:**
- StrokeVision isn't just a data store; it's an intelligent tool.
- It allows authorized staff to manage patient records securely and get instant risk assessments.
- The system was built with a "Security-First" approach, ensuring that sensitive medical data is handled according to strict privacy standards.

---

## Slide 3: System Design & Architecture (SSDLC)
**Title:** Architecture & SSDLC Alignment
**Visual:** [Insert Architecture Diagram from README - Mermaid Chart style]
**Content:**
- **Frontend:** Single Page Application (Vanilla JS) - Fast, Responsive.
- **Backend:** Flask REST API - Secure Gateway.
- **Databases (Separation of Concerns):**
  - **SQLite:** User Auth & Credentials (Isolated).
  - **MongoDB:** Patient Health Records (Scalable).
- **SSDLC Stages:**
  - **Design:** Threat Modeling, DB Separation.
  - **Implementation:** Input Validation, Secure Headers.
  - **Testing:** Pytest (Unit/Integration), Manual Verification.

**Speaker Notes:**
- This architecture diagram maps our system: Frontend SPA communicates via secure JSON/JWT with the Flask API.
- Crucially, we separated concerns: User credentials live in a relational SQLite DB, while flexible patient data resides in MongoDB.
- This limits the "blast radius"—if one DB is compromised, the other remains secure.
- We followed the SSDLC: Security wasn't an afterthought; it was designed into the architecture (DB separation) and implemented via rigorous validation.

---

## Slide 4: Security Features Overview
**Title:** Core Security Implementation
**Content:**
- **Authentication:** Hybrid Session (Flask-Login) + JWT (API).
- **Data Protection:**
  - **Passwords:** Bcrypt Hashing (Work factor 12).
  - **Sessions:** HttpOnly, Secure, SameSite Cookies.
- **Input Validation:**
  - **Server-Side:** Flask-WTF Forms (Strict Type Checking).
  - **Sanitization:** Prevention of XSS & SQL Injection.
- **Network:** CSRF Protection (Global Middleware).

**Speaker Notes:**
- Security is the backbone of StrokeVision.
- We use a hybrid auth model: Sessions for the browser app and JWTs for API scalability.
- Passwords are never stored in plain text; we use **Bcrypt**, which is resistant to rainbow table attacks.
- We enforce strict Input Validation on the server. Client-side checks exist for UX, but the server is the source of truth, blocking malicious payloads like XSS or Injection attempts.
- CSRF tokens are embedded in all state-changing requests.

---

## Slide 5: Database Security & Privacy
**Title:** Secure Data Management
**Content:**
- **Database Separation:**
  - **SQLite:** `users.db` - Stores Admin/Doctor credentials.
  - **MongoDB:** `stroke_vision_db` - Stores Patient Records.
- **Access Control:**
  - Least Privilege Access (Admin vs. Standard User).
  - Connection URI protection via `.env`.
- **Encryption Strategy:**
  - **At Rest:** Password Hashing (Implemented).
  - **Planned:** Field-level encryption for Patient PII (AES).

**Speaker Notes:**
- We purposely decoupled the databases.
- The SQLite database handles authentication. The MongoDB handles patient data.
- This separation enforces granular access controls.
- **Transparency Note:** While passwords are hashed using industry standards, field-level encryption for patient names is a planned enhancement for the next iteration to further align with NHS encryption-at-rest guidelines.

---

## Slide 6: Ethical & Professional Development
**Title:** Ethics & Professional Practice
**Content:**
- **Data Privacy (GDPR/UK DPA):**
  - **Minimization:** Only collecting necessary medical fields.
  - **Consent & Integrity:** Audit logs track who created/edited records.
- **Professional Practices:**
  - **Version Control:** Git/GitHub (Feature Branches, Semantic Commits).
  - **Documentation:** Comprehensive `README.md`, Requirements, Architecture Diagrams.
  - **Testing:** Automated Test Suite (`pytest`) ensuring reliability.

**Speaker Notes:**
- Handling health data brings ethical responsibilities.
- We adhered to **Data Minimization**—collecting only what's needed for the stroke prediction model.
- **Auditability**: Every record has a `created_by` field, ensuring accountability.
- Professionally, I treated this as a production project: using Git branches for features, writing detailed documentation, and maintaining a passing test suite to prevent regressions.

---

## Slide 7: Demonstration Overview (Live)
**Title:** System Demonstration
**Content:**
- **Scenario:** Initial Setup -> Doctor Login -> Patient Management -> Security Checks.
- **Key Flows to Watch:**
  1.  **Secure Registration/Login** (Bcrypt in action).
  2.  **Role-Based Access** (Admin restrictions).
  3.  **CRUD Operations** (Validation errors).
  4.  **Security Defense** (CSRF & XSS blocking).
  5.  **Audit Logs** (Tracking actions).

**Speaker Notes:**
- Now I will switch to a live 10-minute demonstration.
- I'll take you through the lifecycle of a user and a patient record.
- Pay attention to how the system handles errors—it fails securely, without exposing stack traces to the user.

---

## Slide 8: Demo - Authentication & RBAC
**Title:** Demo: Auth & Access Control
**Content:**
- **Action:** Register new user -> Login -> Check Session Cookie.
- **Visual:** Show `HttpOnly` flag in Browser DevTools.
- **Action:** Attempt to access Admin Route as Nurse -> **403 Forbidden**.
- **Evidence:** Show Code Snippet (`@login_required`, `current_user.role`).

**Speaker Notes:**
- (During Demo): I'm logging in as a standard Doctor. Notice the URL redirects securely.
- Only Admins can see the User Management panel. As a Doctor, if I try to force-browse there, the server rejects me with a 403.

---

## Slide 9: Demo - Patient Management & Validation
**Title:** Demo: CRUD & Input Validation
**Content:**
- **Action:** Create Patient Record.
- **Test:** Submit empty form / Invalid Age (150).
- **Result:** Server rejects with specific error messages.
- **Test:** XSS Attempt `<script>alert(1)</script>` in Name field.
- **Result:** Input sanitized or rejected (Flask-WTF).
- **Action:** View Patient Details (Data retrieved from MongoDB).

**Speaker Notes:**
- (During Demo): I'll try to break the form. Entering an age of 200... blocked.
- Creating a patient... success. This data is now in MongoDB.
- This demonstrates the robustness of our Input Validation layer.

---

## Slide 10: Demo - Testing & Code Quality
**Title:** Demo: Testing & Artifacts
**Content:**
- **Action:** Run `pytest -v` in terminal.
- **Visual:** Green passing tests (Auth, Routes, Models).
- **Action:** Show GitHub Commit History.
- **Visual:** "Added Input Validation", "Refactored Auth".

**Speaker Notes:**
- (During Demo): Security isn't just about the app running; it's about verifying it.
- Running the test suite shows that our Auth logic and Model constraints are functioning as expected.
- My git history shows a clear progression of features, backing up the SSDLC claim.

---

## Slide 11: Demo - Audit & Logging
**Title:** Demo: Audit Trails
**Content:**
- **Action:** Perform sensitive action (Delete Patient).
- **Visual:** Check `appmap.log` or Console Output.
- **Log Entry:** `[SECURITY] [LEVEL 1] Deleted patient record: P-123456...`
- **Relevance:** Essential for accountability in healthcare (Non-repudiation).

**Speaker Notes:**
- (During Demo): Every critical action is logged.
- If a record is deleted, we know who did it and when for audit purposes.

---

## Slide 12: OWASP Alignment
**Title:** Mitigating OWASP Top 10
**Content:**
- **A01: Broken Access Control:** Addressed via Role checks & Route protection.
- **A02: Cryptographic Failures:** Addressed via Bcrypt & HTTPS (Ready).
- **A03: Injection:** mitigated by ORM (SQLAlchemy/MongoEngine) & WTForms.
- **A04: Insecure Design:** Addressed via Threat Modeling & DB Separation.

**Speaker Notes:**
- We mapped our defenses against the OWASP Top 10.
- Injection is killed by our ORMs.
- Broken Access Control is handled by our rigorous Permission decorators.

---

## Slide 13: Reflections & Critique
**Title:** Critical Reflection
**Content:**
- **Strengths:** Robust Architecture, Strong Auth, Clean UI/UX.
- **Limitations:**
  - Field-level encryption for Patient Data is not yet fully implemented.
  - MFA (Multi-Factor Auth) is missing.
- **Challenges:** Synchronizing two different databases types (SQL vs NoSQL).

**Speaker Notes:**
- The project was a success, but no system is perfect.
- The dual-database approach was challenging but rewarding for security.
- A key limitation is the lack of stored data encryption for patient fields, which is the immediate next priority.

---

## Slide 14: Future Roadmap
**Title:** Future Improvements
**Content:**
- **Short Term:** Implement `Fernet` (Symetric) encryption for Patient Names/IDs in MongoDB.
- **Medium Term:** Add 2FA/MFA for Doctor logins.
- **Long Term:** Containerize with Docker for secure deployment pipeline.
- **Testing:** Add End-to-End (E2E) tests with Selenium/Playwright.

**Speaker Notes:**
- Moving forward, I would prioritize Field Encryption to fully satisfy the "At Rest" security requirement.
- Dockerizing the app would then ensure that our secure environment is reproducible anywhere.

---

## Slide 15: Conclusion
**Title:** Summary
**Content:**
- **StrokeVision** demonstrates a secure, professional approach to web development.
- **Key Takeaway:** Security is integrated, not bolted on.
- **Outcome:** A functional, defensible, and user-friendly medical tool.
- **Q&A**

**Speaker Notes:**
- In conclusion, StrokeVision meets the learning outcomes by proving that a student project can still adhere to professional security and design standards.
- Thank you for listening.
