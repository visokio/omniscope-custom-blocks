### Salesforce REST connector (OAuth 2.0)

Loads Salesforce data. Authentication uses the OAuth 2.0 **Client Credentials** flow, which is suitable for a headless Omniscope workflow.

#### Salesforce setup
1. In Salesforce Setup, create/configure an **External Client App** with OAuth enabled and the **Manage user data via APIs (`api`)** scope.
2. Enable the **Client Credentials Flow** and configure its **Run As** user in the app policies. That user's Salesforce permissions determine which objects/fields this block can read.
3. Copy the External Client App **Consumer Key** and **Consumer Secret** into the options below.
4. Use your Salesforce **My Domain URL**, e.g. `https://your-company.my.salesforce.com`.

#### Operations
- **Load or Query data**: use a simple way to load objects with all fields, or a the visual query-builder options or paste custom SOQL. Results are retrieved through the synchronous REST Query API and automatically follow `nextRecordsUrl` pages.
- **List available objects**: useful for discovering object API names.
- **Describe fields**: returns field metadata for one object.

**Notes:** REST API access must be enabled for the Salesforce org/edition. Secrets are masked by Omniscope password options.

