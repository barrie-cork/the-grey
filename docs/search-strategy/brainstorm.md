🤔 Areas Needing Clarification
1. Search Query Generation Logic

When domain restrictions are specified AND "Web (without URL limiter)" is checked, how should this work? These seem contradictory - should domains be ignored when "without URL limiter" is selected?
For multiple domains with multiple search types: If I have 3 domains and both web/scholar selected, should we generate:

6 separate queries (3 domains × 2 search types)?
2 queries (one for each search type) with domains handled differently?
Something else?



2. File Type Handling

DOC format: Should "DOC" include both .doc and .docx files, or should they be separate options?
Google Scholar compatibility: Does Google Scholar support filetype: operators? If not, how should file type restrictions be handled for Scholar searches?

3. Session Updates and Activity Logging

When the session name/description is edited on the strategy page, should this create a SessionActivity log entry?
Session name validation: Are there any rules for session names (e.g., must be unique per user, character restrictions)?

4. SearchQuery Model Usage

When should SearchQuery records be created?

When strategy is saved?
Only when "Execute" is clicked?
Should they be ephemeral or stored permanently?


Query tracking: Should we track which specific queries were executed in which search run?

5. Edge Cases and Limits

Maximum terms per category: Should there be a limit on how many terms can be added to each PIC category?
Duplicate terms: Should the system prevent adding the same term twice within a category?
Very long queries: Google has URL length limits (~2000 chars). How should we handle strategies that generate queries exceeding this?
Empty strategy execution: What happens if user clicks "Save & Execute" with no terms? Error message or allow it?

6. URL Generation Details

"Open in Google" with domains: Should the Google search URL include site: restrictions when domains are specified?
File type in direct URLs: Should the direct Google/Scholar links include the filetype: operators?

7. UI Behavior Specifics

Preview update frequency: Should it update on every keystroke (live) or with debouncing (e.g., 500ms delay)?
Term validation: Any restrictions on term content (special characters, length, SQL injection concerns)?
Chip colors: Are the suggested colors (blue for Population, green for Interest, red for Context) acceptable?

8. Integration with SERP Execution

Data format: How exactly does the SERP execution app expect to receive the query data?

Through the SearchQuery model?
Direct JSON passing?
Session status check?


Execution failure: How should we handle if SERP execution app is unavailable or returns an error?

9. Status Management

Strategy with no terms: If a strategy is saved but has no terms in any category, should session status:

Remain as 'draft'?
Change to 'strategy_ready' (since technically they've defined a strategy, just empty)?



10. Copy to Clipboard Behavior

What exactly should be copied?

Just the base PIC query?
Include file type restrictions?
Include domain restrictions?
Full Google search URL?



11. Future SERP Providers

Phase 2 preparation: Besides Google, are there specific SERP providers we should prepare the model structure for (Bing, DuckDuckGo, Yandex, custom APIs)?

12. Performance Considerations

Auto-save: Should we implement auto-save for terms as they're added, or only save on explicit save button?
Large strategies: Any concerns about strategies with hundreds of terms?