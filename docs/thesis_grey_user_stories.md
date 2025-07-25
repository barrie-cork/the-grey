# Thesis Grey: User Stories and Natural Language Requirements

## Project Overview
Thesis Grey is a specialised search application for discovering and managing grey literature in clinical guideline development. This document outlines Phase 1 user stories and requirements for core functionality implementation.

---

## User Authentication & Account Management

### User Stories

**As a researcher**, I want to create an account so that I can access the search application and manage my research sessions.

**As a registered user**, I want to log into the system so that I can access my saved searches and continue my work.

**As a logged-in user**, I want to manage my profile information so that I can keep my account details current.

**As a user**, I want to be automatically redirected to the Review Manager after login so that I can quickly access my work.

### Natural Language Requirements

- The system shall provide a registration form accepting username, email (optional), and password
- The system shall validate registration inputs and provide clear error messages for invalid data
- The system shall securely hash and store user passwords
- The system shall provide a login form with username and password fields
- The system shall implement JWT-based authentication for secure session management
- The system shall automatically redirect authenticated users to the Review Manager page
- The system shall provide a user profile page where users can update their information
- The system shall restrict access to authenticated pages for unauthenticated users
- The system shall provide clear feedback for authentication failures

---

## Review Session Management (Review Manager)

### User Stories

**As a researcher**, I want to see all my review sessions in one place so that I can quickly access and manage my ongoing work.

**As a researcher**, I want to create a new review session so that I can start a new literature search project.

**As a researcher**, I want to see the status of each review session so that I know which ones need attention.

**As a researcher**, I want to navigate directly to the appropriate page based on my session's status so that I can continue my work efficiently.

### Natural Language Requirements

- The system shall display a central Review Manager page as the main landing page after authentication
- The system shall show all review sessions owned by the authenticated user
- The system shall categorise sessions by status (Draft, In Progress, Completed)
- The system shall provide a "Create New Review" button for starting new sessions
- The system shall allow users to click on sessions to navigate to appropriate pages:
  - Draft sessions → Search Strategy page
  - Executing sessions → Search Execution Status page
  - Completed sessions → Results Overview page
- The system shall display basic session information (name, description, creation date, status)
- The system shall provide visual indicators for session status
- The system shall handle empty states when no sessions exist

---

## Search Strategy Development

### User Stories

**As a researcher**, I want to create and configure search strategies so that I can define what literature to search for.

**As a researcher**, I want to organise my search concepts using the PIC framework (Population, Interest, Context) so that I can structure my search systematically.

**As a researcher**, I want to select specific domains and file types so that I can focus my search on relevant sources.

**As a researcher**, I want to see a preview of my generated queries so that I can understand what will be searched.

**As a researcher**, I want to save my search strategy so that I can execute it later or modify it as needed.

### Natural Language Requirements

- The system shall provide a Search Strategy page accessible from the Review Manager
- The system shall allow users to enter search terms organised by PIC categories:
  - Population: terms describing the target population
  - Interest: terms describing the intervention or phenomenon of interest
  - Context: terms describing the setting or context
- The system shall provide domain selection options for targeting specific types of sources
- The system shall offer file type filtering options (PDF, DOC, HTML, etc.)
- The system shall generate search queries automatically based on entered concepts
- The system shall display a real-time preview of generated queries
- The system shall validate search strategy inputs and provide helpful error messages
- The system shall save search strategies to the database when users submit the form
- The system shall allow users to modify existing search strategies for draft sessions
- The system shall provide clear navigation to execute searches once strategy is defined

---

## Search Execution and Monitoring

### User Stories

**As a researcher**, I want to execute my search strategy across multiple search engines so that I can gather comprehensive results.

**As a researcher**, I want to monitor the progress of my search execution so that I know when it's complete.

**As a researcher**, I want to see if any errors occur during search execution so that I can address them.

**As a researcher**, I want to be automatically redirected to results when search execution completes so that I can begin reviewing findings.

### Natural Language Requirements

- The system shall integrate with Google Search API via Serper for search execution
- The system shall execute all queries defined in a search strategy
- The system shall provide a Search Execution Status page showing:
  - Overall progress (queries completed/total)
  - Individual query status
  - Any error messages
  - Estimated completion time
- The system shall handle search execution asynchronously to prevent blocking
- The system shall store raw search results in the database as they're retrieved
- The system shall implement basic pagination handling for large result sets
- The system shall provide error handling for API failures, rate limits, and network issues
- The system shall update execution status in real-time
- The system shall automatically transition users to Results Overview when execution completes
- The system shall allow users to cancel ongoing searches if needed

---

## Results Processing and Management

### User Stories

**As a researcher**, I want search results to be automatically processed and normalised so that I can work with clean, consistent data.

**As a researcher**, I want to view all my search results in a organised interface so that I can begin reviewing them.

**As a researcher**, I want to filter and sort results so that I can focus on the most relevant items first.

**As a researcher**, I want to see basic metadata for each result so that I can quickly assess relevance.

### Natural Language Requirements

- The system shall automatically process raw search results into normalised format
- The system shall perform URL normalisation to ensure consistency
- The system shall extract basic metadata including:
  - Domain/source
  - File type
  - Publication indicators
- The system shall provide a Results Overview page displaying processed results
- The system shall implement filtering options by:
  - Domain
  - File type
  - Review status
  - Date ranges
- The system shall implement sorting options by:
  - Relevance score
  - Date
  - Source
  - Review status
- The system shall display result previews including title, URL, and snippet
- The system shall handle large result sets with pagination or virtual scrolling
- The system shall provide search within results functionality
- The system shall maintain traceability to original search queries

---

## Results Review and Annotation

### User Stories

**As a researcher**, I want to tag results as included, excluded, or maybe so that I can categorise them for my review.

**As a researcher**, I want to provide exclusion reasons when I exclude results so that I can document my decision-making process.

**As a researcher**, I want to add notes to individual results so that I can capture my thoughts and observations.

**As a researcher**, I want to track my review progress so that I know how much work remains.

**As a researcher**, I want to filter results by review status so that I can focus on unreviewed items.

### Natural Language Requirements

- The system shall provide tagging functionality with predefined options:
  - Include: results that meet inclusion criteria
  - Exclude: results that don't meet criteria
  - Maybe: results requiring further consideration
- The system shall require exclusion reasons when users tag results as "Exclude"
- The system shall provide common exclusion reason options plus free text
- The system shall allow users to add notes to individual results
- The system shall support rich text formatting in notes
- The system shall display review progress indicators showing:
  - Total results count
  - Reviewed vs unreviewed counts
  - Distribution of include/exclude/maybe tags
- The system shall provide filtering by review status
- The system shall save all review actions immediately to prevent data loss
- The system shall support bulk operations for efficient reviewing
- The system shall maintain PRISMA-compliant workflow documentation
- The system shall timestamp all review actions for audit trails

---

## Reporting and Export

### User Stories

**As a researcher**, I want to generate reports showing my search and review statistics so that I can document my methodology.

**As a researcher**, I want to export my results in multiple formats so that I can use them in other tools and publications.

**As a researcher**, I want to see PRISMA flow diagram data so that I can create publication-ready documentation.

**As a researcher**, I want to view summary statistics about my search results so that I can understand the scope of my review.

### Natural Language Requirements

- The system shall provide a Reporting page accessible from completed sessions
- The system shall generate basic PRISMA flow diagram data including:
  - Records identified through database searching
  - Records screened
  - Records excluded with reasons
  - Full-text articles assessed for eligibility
  - Studies included in review
- The system shall display summary statistics including:
  - Total results by source
  - Results by domain/file type
  - Tag distribution (include/exclude/maybe)
  - Review completion percentage
- The system shall support export in multiple formats:
  - CSV: for data analysis
  - JSON: for programmatic use
  - Basic PDF: for documentation
- The system shall include all relevant metadata in exports
- The system shall allow users to select which data to include in exports
- The system shall provide export of both full results and filtered subsets
- The system shall generate exports quickly for reasonable result set sizes
- The system shall maintain data integrity and formatting in all export formats

---

## System Architecture and Performance

### User Stories

**As a user**, I want the application to respond quickly so that I can work efficiently.

**As a user**, I want my data to be saved reliably so that I don't lose my work.

**As a developer**, I want the code to be well-organised so that I can maintain and extend it easily.

### Natural Language Requirements

- The system shall follow Vertical Slice Architecture principles for maintainability
- The system shall use PostgreSQL database with proper indexing for performance
- The system shall implement proper error handling and logging throughout
- The system shall provide loading indicators for long-running operations
- The system shall use Prisma ORM for type-safe database operations
- The system shall implement proper data validation on both client and server
- The system shall use React with modern hooks for efficient UI updates
- The system shall implement proper state management for complex interactions
- The system shall provide responsive design for various screen sizes
- The system shall implement proper security measures including:
  - Input sanitisation
  - SQL injection prevention
  - XSS protection
  - CSRF protection
- The system shall handle concurrent user operations safely
- The system shall provide proper backup and recovery mechanisms

---

## Acceptance Criteria Templates

### For Authentication Stories:
- [ ] User can successfully register with valid credentials
- [ ] User receives appropriate error messages for invalid inputs
- [ ] User can log in with correct credentials
- [ ] User is redirected to Review Manager after successful login
- [ ] User cannot access protected pages without authentication
- [ ] User can update profile information successfully

### For Search Strategy Stories:
- [ ] User can create new search strategies
- [ ] User can organise concepts using PIC framework
- [ ] User can select domains and file types
- [ ] User can see real-time query preview
- [ ] User can save and modify strategies
- [ ] Form validation works correctly

### For Search Execution Stories:
- [ ] Searches execute successfully with valid API integration
- [ ] Progress is tracked and displayed accurately
- [ ] Errors are handled gracefully with clear messages
- [ ] Results are stored correctly in database
- [ ] User is redirected to results when complete

### For Results Review Stories:
- [ ] Results display correctly with all metadata
- [ ] Filtering and sorting work as expected
- [ ] Tagging functionality works correctly
- [ ] Notes can be added and saved
- [ ] Progress tracking is accurate
- [ ] Bulk operations work efficiently

### For Reporting Stories:
- [ ] Reports generate correctly with accurate data
- [ ] Exports work in all specified formats
- [ ] PRISMA data is calculated correctly
- [ ] Summary statistics are accurate
- [ ] Export files contain expected data structure

---

## Technical Implementation Notes

### Database Considerations:
- Implement proper indexing for search performance
- Use foreign key constraints for data integrity
- Plan for data archival and cleanup procedures
- Consider read replicas for reporting queries

### API Integration:
- Implement proper rate limiting for external APIs
- Add retry logic for failed requests
- Cache results where appropriate
- Monitor API usage and costs

### Performance Optimisation:
- Implement pagination for large result sets
- Use database queries efficiently
- Optimise React rendering with proper memoisation
- Implement lazy loading where appropriate

### Security Measures:
- Validate all inputs on both client and server
- Implement proper session management
- Use HTTPS for all communications
- Regular security updates and monitoring