# Results Review Feature: UX and UI Implementation Plan

---
**Phase:** Both (Core review in Phase 1, advanced collaboration in Phase 2)
---

## Overview

The Results Review feature provides researchers with interfaces for evaluating, categorising, and annotating processed search results. Phase 1 focuses on the `Results Overview Page` for listing and basic tagging, potentially linking to a simple `Review Interface Page` for individual items. Phase 2 enhances collaboration, conflict resolution, and integrates advanced features like full-text review.

## Core Requirements

This section outlines the core functional and technical requirements for the Review Results feature, stratified by development phase. These requirements are derived from the overall project requirements (`project_docs/requirements/core_requirements.md`) and are specific to this feature's UI/UX implementation.

### Phase 1 Requirements

#### Functional Requirements
- **REQ-FR-RR-1:** System must provide a `Results Overview Page` (`/results-overview/:sessionId`) displaying processed results for a session.
- **REQ-FR-RR-2:** The `Results Overview Page` must support basic filtering (tag status, type) and sorting.
- **REQ-FR-RR-3:** Users must be able to apply basic tags (Include, Exclude, Maybe) to results, potentially directly on the overview or via a dedicated `Review Interface Page` (`/review/:resultId`).
- **REQ-FR-RR-4:** When tagging as "Exclude", users must provide a reason.
- **REQ-FR-RR-5:** Users must be able to add simple notes to individual results (likely on the `Review Interface Page`).
- **REQ-FR-RR-6:** Progress tracking (counts/percentage tagged) should be visible, likely on the `Results Overview Page`.
- **REQ-FR-RR-7:** Individual result details (title, snippet, URL, metadata) must be viewable.

#### Technical Requirements
- **REQ-TR-RR-1:** Tagging/notes update `ReviewTagAssignment` / `Note` entities.
- **REQ-TR-RR-2:** `Results Overview Page` must handle large lists (virtualization/pagination).
- **REQ-TR-RR-3:** Actions should auto-save.

### Phase 2 Requirements (Enhancements)

#### Functional Requirements
- **REQ-FR-RR-P2-1:** Support custom tagging on the `Review Interface Page`.
- **REQ-FR-RR-P2-2:** Multi-reviewer support (assignment, progress tracking) visible on `Results Overview Page` and potentially `Session Hub Page`.
- **REQ-FR-RR-P2-3:** Conflict detection/resolution tools (potentially on `Results Overview` or a dedicated conflict view).
- **REQ-FR-RR-P2-4:** Interface for resolving duplicates identified by Results Manager (potentially linked from `Results Overview` or on `Deduplication Overview Page`).
- **REQ-FR-RR-P2-5:** Full-text preview/annotation on the `Review Interface Page`.
- **REQ-FR-RR-P2-6:** AI assistance (suggestions) on the `Review Interface Page`.
- **REQ-FR-RR-P2-7:** Enhanced analytics/visual feedback.

#### Technical Requirements
- **REQ-TR-RR-P2-1:** Collaborative features require real-time updates/concurrent handling.
- **REQ-TR-RR-P2-2:** Duplicate management UI needs clear presentation/resolution actions.
- **REQ-TR-RR-P2-3:** Full-text integration requires performant viewer/annotation.

## Phase 1 Implementation

---
**Phase:** Phase 1
---

### 1. Results Review Feature Structure

#### Standard Pages & Components:

*   **Results Overview Page (`/results-overview/:sessionId`):**
    *   Displays the list of `ProcessedResult` entities for the session.
    *   Primary interface for filtering, sorting, and getting an overview of review progress.
    *   May allow quick tagging actions directly on list items.
    *   Provides navigation to the detailed `Review Interface Page` for each result.
*   **Review Interface Page (`/review/:resultId`):**
    *   Focused view for a *single* `ProcessedResult`.
    *   Displays all details, metadata, snippet, URL.
    *   Primary location for applying tags (Include/Exclude/Maybe), exclusion reasons, and adding notes.
    *   May include a simple preview if available.
*   **Result List Item (Component on `Results Overview Page`):**
    *   Compact representation of a result.
    *   Shows key info (title, source, type, tag status).
    *   Includes link/button to navigate to the `Review Interface Page` (`/review/:resultId`).
    *   May include quick tag buttons.

#### Workflow & Transitions:

**Workflow (Reviewing Results):**

1.  User navigates from `Search Execution Status Page` (or `Session Hub Page` in P2) to the `Results Overview Page` (`/results-overview/:sessionId`) once results are processed.
2.  User browses the list, using filters/sort controls as needed.
3.  User selects a result to review in detail, navigating to the `Review Interface Page` (`/review/:resultId`).
4.  On the `Review Interface Page`, the user examines the result, applies a tag (Include/Exclude/Maybe), adds an exclusion reason if needed, and optionally adds notes.
5.  Actions are auto-saved.
6.  User navigates back to the `Results Overview Page` (or potentially to the next/previous result's `Review Interface Page`).
7.  Progress indicators on the `Results Overview Page` update.

*(Refer to `workflow.mmd` for the visual flow.)*

**Navigation:**

*   **Access Overview:** From `/search-execution/:sessionId` (or `/session-hub/:sessionId` in P2) -> `/results-overview/:sessionId`.
*   **Access Detail:** From `/results-overview/:sessionId` -> `/review/:resultId`.
*   **Return/Next:** From `/review/:resultId` -> `/results-overview/:sessionId` (or potentially `/review/:nextResultId`).

#### Role-Based Access (Phase 1):

*   **Reviewer, Lead Reviewer (P2), Admin:** Can view overview/interface, apply tags, add notes.
*   **Researcher:** Can typically view overview/interface, potentially add notes (TBD), but may not have tagging permissions depending on setup.
*   **User:** View-only access typically.

*(Refer to `project_docs/standards/role_access_matrix.md` for full details.)*

### 2. UI Components

#### Results Overview Page Layout

* **Header Section:**
  * Session title and description
  * Progress bar showing overall review completion percentage
  * Summary statistics (total results, tagged counts by category)
  * Action buttons (export, report, filtering options)

* **Controls Section:**
  * Search box for filtering results by title, snippet, or URL
  * Filter dropdowns (by tag status, document type, source)
  * Sort controls (by relevance, date, title)
  * Display density toggle (compact/comfortable viewing)
  * Results per page selector (25/50/100)

* **Results List:**
  * Virtualized scrolling list for handling large result sets efficiently
  * Compact row format with expandable details
  * Visual indicators for document type (PDF, DOC, website)
  * Tag indicators using colour-coded badges (green for included, red for excluded, yellow for maybe)
  * Visited URL indicators
  * Pagination controls at bottom

#### Result List Item Component (on Results Overview)

* **Collapsed View:**
  * Checkbox for bulk selection
  * Title (truncated if necessary)
  * Organisation/source (domain extracted from URL)
  * Document type badge
  * Tag status badge
  * Quick action buttons (expand, view external, tag options)

* **Expanded View:**
  * Full title and snippet
  * Complete metadata panel
  * Document preview panel (when available)
  * Tagging controls with exclusion reason field
  * Notes input area with auto-save
  * Actions menu (copy citation, mark for follow-up)

#### Review Interface Page Layout

* **Expanded View:**
  * Focused layout for one result.
  * Displays full title, snippet, URL, all metadata.
  * Clear controls for selecting Include/Exclude/Maybe tags.
  * Exclusion reason dropdown/input (conditional on Exclude tag).
  * Notes text area.
  * Buttons for navigation (Back to Overview, Next/Previous Result).

### 3. Interaction Patterns

#### Tagging Workflow

* **One-click Tagging:** Quick tag buttons available directly in each result row
* **Detailed Tagging:** Expanded view provides tag options with additional context fields
* **Required Justification:** "Exclude" tag requires selection of exclusion reason
* **Auto-save:** All tagging actions and notes saved automatically
* **Visual Feedback:** Immediate update of result status and progress indicators

#### Navigation and Efficiency

* **Continuous Scrolling:** Efficient review of multiple results without page reloads
* **Sticky Headers:** Controls remain visible whilst scrolling through results
* **Contextual Actions:** Most common actions accessible directly in result rows
* **Bulk Operations:** Select multiple results for batch tagging (by domain or type)
* **Filter Persistence:** Filters and sort preferences maintained during session

### 4. Visual Design and Styling Guidelines

This section details the specific visual styling for the Review Results feature, primarily the **Results Overview Page**, drawing from the global Thesis Grey UI/UX Style Guide.

#### 4.1. Overall Page Layout (Results Overview Page)

*   **Page Backgrounds:** Pure White (`#FFFFFF`) for light mode; Dark Charcoal (`#3C3F41`) for dark mode.
*   **Header Section:**
    *   Typography for Session Title/Description: H2 (20px, Medium) for title, Body Text (14px, Regular) for description. Dark Charcoal (light) / White (dark) text.
    *   Progress Bar: Teal (`#6A9CAB`) fill for progress against a Light Taupe (`#E4E0D5`) (light mode) or Slate (`#4A5662` - darker variant) (dark mode) track.
    *   Summary Statistics: Body Text (14px, Regular or Medium weight for emphasis). Text colors matching mode.
    *   Action Buttons (Export, Report): Styled as Primary (Teal `#6A9CAB`) or Secondary (Slate `#5D6977` light / Light Taupe `#CEC9BC` dark) buttons.
*   **Controls Section (Search, Filters, Sort):**
    *   Search Box: Standard Thesis Grey input field styling (White/Light Taupe border in light mode; Slate/darker border in dark mode; Teal focus border).
    *   Filter Dropdowns/Sort Controls: Standard form component styling. Active filters or sort criteria can be indicated with a Teal (`#6A9CAB`) accent.
    *   Display Density Toggle/Results per Page Selector: Styled as segmented buttons or a simple dropdown, following button/form styling. Teal accent for the active state.

#### 4.2. Results List & Pagination

*   **List Container:** Typically part of the page background. If distinct (e.g., within a card), use standard card styling.
*   **Pagination Controls:**
    *   Buttons for page numbers and navigation (next/prev): Styled as Secondary Buttons. The current page number button can have a Teal (`#6A9CAB`) background or border to indicate active state.

#### 4.3. Result Row Component (Collapsed and Expanded Views)

*   **General Row Styling:**
    *   Background: Transparent (inheriting from list/page) by default.
    *   Hover State: Subtle background change (e.g., Lighter Taupe (`#E4E0D5`) in light mode, a slightly lighter Slate in dark mode) or a Teal (`#6A9CAB`) left border.
    *   Selected State (for bulk actions): A light Teal (`#8BBAC7` with opacity) background tint.
    *   Borders: Subtle Light Taupe / Slate border between rows.
*   **Typography:**
    *   Title: H3 style (16px, Medium) or Body Text (14px, Medium). Clickable link styled with Teal (`#6A9CAB`) text color.
    *   Organisation/Source, Snippet, Metadata: Body Text (14px, Regular) or Small/Caption text (12px, Regular). Primary text color for snippet, secondary text colors (Slate/Light Taupe) for less prominent metadata.
*   **Visual Indicators:**
    *   **Document Type Badges (PDF, DOC, etc.):** Small, pill-shaped (`px-2 py-0.5`). Use Slate Blue-Gray (`#5D6977`) background with White text for a neutral, consistent look, or consider specific icons without a strong background color.
    *   **Tag Status Badges:** Pill-shaped (`px-2 py-0.5`). Ensure high contrast for text.
        *   Include: Teal (`#6A9CAB`) background, White (`#FFFFFF`) text.
        *   Exclude: Error Red (`#D64045`) background, White (`#FFFFFF`) text.
        *   Maybe: Amber/Yellow (e.g., `#F59E0B` - requires palette confirmation) background, Dark Charcoal (`#3C3F41`) or White text.
        *   Pending Review: Slate Blue-Gray (`#5D6977`) background, White (`#FFFFFF`) text.
    *   **Visited URL Indicators:** Change link color of the title to a darker Teal (`#4A7A89`) or Slate Blue-Gray (`#5D6977`).
*   **Interactive Elements within Row:**
    *   **Checkbox (Bulk Selection):** Standard form control styling, Teal (`#6A9CAB`) accent when checked.
    *   **Quick Action Buttons (Expand, View External):** Icon buttons. Icon color Teal (`#6A9CAB`) on hover/focus.
    *   **Tagging Controls (Buttons: Include, Exclude, Maybe in expanded view):**
        *   Can be small buttons. "Include": Primary Teal. "Exclude": Button with Error Red (`#D64045`) text or border. "Maybe": Secondary Slate/Light Taupe button.
    *   **Exclusion Reason Field:** Standard dropdown/input styling.
    *   **Notes Input Area:** Standard textarea styling (White/Light Taupe border in light mode; Slate/darker border in dark mode; Teal focus border).
    *   **Document Preview Panel (Expanded View):** If shown, use a card-like container or a simple border around the preview area.

#### 4.4. Styling for Phase 2 Enhancements

*   **Keyboard Shortcut Hints:** If displayed, use Small/Caption text (12px) in a non-obtrusive manner.
*   **Conflict Indicators (on result rows):** Small icon (e.g., warning triangle) with Error Red (`#D64045`) or Amber/Yellow color.
*   **Conflict Resolution Interface:** Side-by-side comparison panels can use card styling. Decision controls (buttons) follow primary/secondary styling; Lead Reviewer's resolution button prominently styled (Teal).
*   **Duplicate Grouping/Indicators:** Visually group items with a subtle shared border or alternating very light background tints if multiple groups are visible. Similarity scores: Body Text (14px).
*   **Duplicate Resolution Controls:** Merge/Keep buttons: Primary Teal. Discard: Secondary or subtle Error Red accent.
*   **Advanced Metadata Panel:** Use standard card styling. Typography as per data hierarchy.
*   **Full-text Preview Styling:** Clear, readable Body Text. Highlighting tools should use a standard yellow highlight that offers good contrast for text underneath. Annotation icons/controls: subtle icon buttons.
*   **AI Tagging Suggestions:** Display suggestions clearly, perhaps in a dismissible small card or section. Confidence scores: Small/Caption text. Use Teal accents for suggested actions.

#### 4.5. Mode Switching

*   The entire Results Overview Page and all its components (header, controls, list, rows, expanded views, modals) must fully support the application's light/dark mode switching, using CSS variables or Tailwind's `dark:` prefix.

#### 4.6. Accessibility

*   **Contrast Ratios:** Critical for text on colored badges (Tag Status), highlighted text, and all UI controls. Must meet WCAG AA.
*   **Focus States:** All interactive elements (buttons, links, input fields, checkboxes, tabs, pagination controls, items in lists if individually focusable) require a visible Teal (`#6A9CAB`) outline on focus.
*   **ARIA Attributes:** Essential for the virtualized list, result rows (as list items), interactive controls within rows, pagination, dynamic status updates, and any modal dialogs (e.g., for detailed view or notes).
*   **Keyboard Navigation:** Ensure logical navigation flow through the page, into and out of result rows, and within expanded views.

## Phase 2 Enhancements

---
**Phase:** Phase 2
---

(Enhancements primarily affect the `Review Interface Page` and add collaborative aspects visible on the `Results Overview Page`.)

### 1. Advanced Interaction Features (Keyboard)

#### Keyboard Navigation and Shortcuts

* **Focus Management:**
  * Tab key navigation through all interactive elements
  * Up/Down arrow keys to move between results
  * Enter/Space to expand/collapse the selected result
  * Keyboard shortcuts for common actions:
    * `I` - Tag as Include
    * `E` - Tag as Exclude
    * `M` - Tag as Maybe
    * `N` - Add/edit note
    * `O` - Open link in new tab
    * `F` - Focus search/filter box
    * `J`/`K` - Navigate to next/previous result

* **Accessibility Enhancements:**
  * Screen reader announcements for status changes
  * High contrast mode support
  * Keyboard focus indicators
  * ARIA attributes for complex interactions

### 2. Collaborative Review Features

#### Multi-reviewer Support

* **Reviewer Assignment Panel:**
  * Assigns specific reviewers to results or result sets
  * Displays reviewer progress and statistics
  * Allows for reassignment and workload balancing

* **Conflict Detection:**
  * Automatic identification of conflicting tags between reviewers
  * Visual indicators for conflicts in result rows
  * Filtering option to view only conflicts

* **Conflict Resolution Interface:**
  * Side-by-side comparison of conflicting reviews
  * Lead reviewer controls for resolving conflicts
  * Commenting system for reviewer discussion
  * Decision tracking and audit trail

### 3. Advanced Result Management

#### Duplicate Management

* **Duplicate Detection Indicators:**
  * Visual grouping of potential duplicates in the results list
  * Similarity score display
  * Filter option to view grouped duplicates

* **Duplicate Resolution Controls:**
  * Merge button to combine duplicate entries
  * Keep/discard controls for choosing primary entry
  * Manual linking/unlinking of results

#### Enhanced Metadata and Analysis

* **Advanced Metadata Panel:**
  * Publication date extraction and normalisation
  * Author information
  * Citation count (when available)
  * Related documents section

* **Full-text Integration:**
  * Preview of full-text content when available
  * Text highlighting and annotation tools
  * Automatic relevant section identification
  * Citation extraction

### 4. AI-assisted Review

* **Smart Tagging Suggestions:**
  * AI-generated tag recommendations based on content analysis
  * Confidence scores for suggestions
  * Learning from reviewer decisions

* **Similarity Analysis:**
  * Automatic grouping of thematically similar results
  * Topic modelling visualisation
  * Concept mapping between results

* **Review Acceleration Tools:**
  * Bulk tagging recommendations
  * Automated exclusion suggestions for out-of-scope content
  * Priority ordering based on relevance prediction

### 5. Enhanced Visual Feedback

* **Interactive Progress Visualisation:**
  * Detailed breakdown charts of review progress
  * Real-time updates during tagging
  * Team member contribution visualisation
  * Time-tracking and productivity metrics

* **Advanced Filtering and Search:**
  * Natural language search within results
  * Semantic similarity search ("find more like this")
  * Advanced boolean filtering
  * Saved filter presets

## Implementation Guidelines

### Technical Approach

1. **Progressive Enhancement:**
   * Build Phase 1 core functionality with extensibility in mind
   * Design component interfaces that can accommodate Phase 2 features
   * Use composition patterns to allow feature insertion without refactoring

2. **Performance Considerations:**
   * Implement virtualized scrolling for large result sets
   * Use optimistic UI updates for immediate feedback
   * Implement efficient background saving with debouncing
   * Consider pagination or infinite scrolling for very large reviews

3. **Accessibility Compliance:**
   * Ensure WCAG 2.1 AA compliance from Phase 1
   * Test with screen readers and keyboard-only navigation
   * Implement proper focus management and aria attributes
   * Provide sufficient colour contrast and alternative indicators

4. **Responsive Design:**
   * Optimize layout for different screen sizes
   * Consider touch interfaces for tablet usage
   * Adapt information density based on available screen real estate
   * Ensure critical actions remain accessible on smaller screens

### Integration Points

1. **Database Integration:**
   * Direct integration with ProcessedResult, ReviewTag, and Note entities
   * Real-time updates via WebSocket for collaborative features
   * Efficient querying with pagination and filtering at the database level

2. **Search Strategy Integration:**
   * Display relevant search strategy information for context
   * Allow refinement of search from within review interface
   * Track results across different search executions

3. **Reporting Integration:**
   * Export review progress data for reports
   * Provide hooks for PRISMA diagram generation
   * Generate citation lists from included results

This implementation plan provides a comprehensive roadmap for developing the Review Results feature, focusing on creating an efficient, user-friendly experience that scales from individual researchers to collaborative teams across both Phase 1 and Phase 2 of the project.