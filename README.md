# Online Banking Management System (OBMS)

A robust, secure, and modern 24/7 web-based banking application designed to transition traditional, manual financial services into a high-performance digital ecosystem. The platform features a dual-portal design that provides customers with automated wealth management tools and equips bank administrators with a centralized oversight engine to monitor platform-wide liquidity, verify identities, and prevent fraud.

---

## 🚀 Core Modules & Features

### 👤 1. Customer Portal
* **Onboarding & KYC:** Streamlined user registration collecting personal details, physical addresses, and tax identifiers (PAN). New accounts are placed in a secure `Pending` state until manually vetted by bank staff.
* **Unified Banking Dashboard:** Dynamic single-view dashboard managing multiple account tiers (Savings, Checking, and Credit Cards) featuring real-time analytics for income/spending patterns and a privacy-centric eye-icon balance visibility toggle.
* **Transaction Engine:** Supports instantaneous peer-to-peer (P2P) transfers via internal routing, external bank transfers, and automated recurring transfer scheduling (Daily, Weekly, Monthly).
* **Financial Products Application:** Integrated digital application forms for tiered credit cards (Silver, Gold, Platinum) and various loan structures (Home, Personal, Vehicle).
* **Utility Bill Payments:** Dedicated module to track, manage, and settle utility statements alongside a stored Payee/Beneficiary list for faster future routing.
* **Support Desk:** A built-in asynchronous complaint ticketing pipeline where customers can submit technical or account queries and track resolution updates in real time.

### 🛠️ 2. Admin Dashboard (Centralized Oversight Console)
* **Operational Analytics:** High-level system vitals interface tracking total platform liquidity, active member counts, and live transaction pulses.
* **User Lifecycle Control:** Comprehensive authority to manage user status, adjust permissions, edit profiles, reset account passwords, or terminate accounts due to policy violations.
* **Fraud Prevention & Underwriting:** Centralized verification queue to review and override high-value or suspicious transaction flags, assess loan risks, assign credit limits, and disburse approved loan funds directly into user balances.
* **Support Ticket Processing:** Ticket management desk enabling admins to triage and update customer complaints (`Pending` ➡️ `In Progress` ➡️ `Resolved`), which triggers instant user notification pathways.

---

## 🧱 Technical Stack & Architecture

### Frontend (User Experience)
* **HTML5 & CSS3:** Structural grid engine crafted for clean navigation layouts and high visual stability.
* **JavaScript:** Used to power interactive UI behaviors, balance view toggling, and client-side page responsiveness.
* **Vue.js:** Integrated directly within the UI layout to supply dynamic state reactivity without the performance overhead of an completely isolated frontend application package.
* **System-Wide Dark Mode:** Fully responsive template framework incorporating a global night-mode toggle to maximize usability across varying screens and lighting parameters.

### Backend & Core Logic
* **Python & Django Framework:** Powers the core financial workflows, role-based access control (RBAC), secure URL routing, and server-side model validation constraints.
* **Django ORM:** Implemented to enforce strict relationship integrity, handle database abstraction layer definitions, and prevent low-level query insertion errors.
* **Session Management:** Robust server-side session allocation ensuring consistent user identity mapping across protected banking sub-pages.

### Database Tier
* **SQLite (Local Dev):** Highly efficient relational database file structuring used out of the box for atomic ledger logging during prototyping stages. Fully optimized for seamless migration mapping onto high-availability systems (such as **PostgreSQL** or **MySQL**) for production scale.

---

## 🗃️ Relational Database Table Schemas

The data layer utilizes a normalized schema layout (1NF, 2NF, 3NF compliant) to eliminate storage redundancy and ensure financial data consistency. Key tables include:

### 1. User Master Table (`auth_user`)
| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key, Auto-Increment | Unique user account identifier. |
| `username` | String (Max 150) | Unique, Required | Unique login credential alias. |
| `email` | String (Max 254) | Required | Customer's primary contact email. |
| `password` | String (Max 128) | Required | Secure PBKDF2 hashed password string. |
| `is_staff` | Boolean | Default: `false` | Administrative access flag. |
| `is_active` | Boolean | Default: `true` | Account activation toggle status. |

### 2. Customer Profile Extension (`main_customerprofile`)
| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | Unique row identity code. |
| `user_id` | Integer | Unique, Foreign Key ➡️ `auth_user(id)` | Maps directly to core credentials profile. |
| `phone_number` | String (Max 15) | Optional | Contact number sequence. |
| `address` | Text | Optional | Registered physical residency details. |
| `pan_number` | String (10) | Optional | Tax identification sequence. |
| `is_approved` | Boolean | Default: `false` | KYC status validation state assigned by Admin. |

### 3. Core Account Ledger (`main_account`)
| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | Unique row identifier. |
| `user_id` | Integer | Foreign Key | Owner reference profile. |
| `account_number`| String (12) | Unique, Required | Unique 12-digit standard banking account number. |
| `account_type` | String (Max 20) | Enum | Account classification (e.g., Savings, Checking). |
| `balance` | Decimal (12,2) | Default: `0.00` | Current real-time account ledger balance. |
| `card_type` | String (Max 20) | Optional | Current tier of issued payment card if applicable. |

### 4. Transaction History Table (`main_transaction`)
| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | Transaction row identifier. |
| `account_id` | Integer | Foreign Key | Originating/source account identifier. |
| `receiver_account_id`| Integer | Optional, Foreign Key | Recipient account identifier. |
| `amount` | Decimal (10,2) | Required | Precise financial quantity transferred. |
| `transaction_type` | String (Max 10) | Enum | Activity tracking label (`CREDIT` / `DEBIT`). |
| `status` | String (Max 10) | Enum | Operational state (e.g., Pending, Success, Reverted). |
| `description` | String (Max 255) | Required | Contextual transaction reference memo notes. |

---

## 🏗️ System Processing Flows (Data Flow Diagrams)

* **Level 0 (Context Level):** Outlines clear transaction parameters dividing core execution processes from external elements including Customers, Bank Staff, and System Admins tracking balance fetches, file claims, and asset routing.
* **Level 1 (Sub-System Breakdown):** Completely isolates platform micro-logic boundaries across 4 architectural processing units: Identity/User Management, Account & Transaction Processing, Product Sales/Underwriting, and Auditing/System Logging.
* **Level 2 (Transaction Validation Layer):** Routes every input string through runtime verification checkpoints enforcing account balance boundaries, format standards, and credential validations prior to modifying state ledgers.

---

## ⚙️ Installation & Local Server Setup

### Hardware Prerequisites
* **Minimum:** Dual-core CPU, 4 GB RAM, 1 GB free storage space.
* **Recommended:** Intel i3/Ryzen 3 or better, 8 GB RAM, 2 GB+ free storage space.

### Step-by-Step Deployment
Follow these commands to configure the development environment locally:

**1. Clone and Navigate to the Repository**
```bash
git clone [https://github.com/YOUR_USERNAME/online-banking-system.git](https://github.com/YOUR_USERNAME/online-banking-system.git)
cd online-banking-system
