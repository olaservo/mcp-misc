We maintain a repository containing a collection of reference implementations for the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP), as well as a Readme containing a list of links to community built MCP servers, official MCP servers and additional resources: https://github.com/modelcontextprotocol/servers 

We've collected a dataset of all open official MCP server PRs in batched CSV files saved to this directory: {{output_location}}

OUR CURRENT TASK: 

Since this is an official repository for MCP, our job is to review each link to make sure that any server we add to this list meets the following guidelines at minimum:

- The link MUST go to a code repository for an MCP Server
- Any images or icons used in links must point to a valid image (i.e. it must not return a 404)
- The organization maintaining or owning the repository is valid as the owner/maintainer of the official repository
- There are no red flags related to security or other aspects of the repo
- There MUST be documentation that indicates how to install it

**IMPORTANT: Before validating each server, check if the `Validation_Status` column is already marked as "Valid". If it is, this indicates the PR was already approved and you should skip validation for that server - simply copy the row as-is to your output CSV.**

For servers that need validation (where `Validation_Status` is empty):

Use the `fetch` tool to look at the first chunk of each repo's Readme and then create a new csv which labels the result of the validation.  You MUST check each link explicitly to ensure it meets these minimum requirements.

If we are over 90% confident the link is for a legitimate server, mark it as Valid.  Otherwise, mark it as either Potentially Valid or Invalid corresponding to your confidence level.

The columns in the validation results CSV must include the column names below:

PR_Number,PR_Title,Complete_Line,Server_URL,Server_Name,PR_Author,Validation_Status,Is_Valid_Confidence_Level,Validation_Notes,Category

The validation output must be saved here: {{output_location}}/validation_results with file naming convention `server_addition_prs_official_batch_{number}_validation.csv`

NOTE: ONLY review and validate links from the current file {{current_file_name}} in order to maintain review quality.

After we finish our review session, lets prepare the prompt for our next review session by copying this prompt verbatim and updating the current file name to review to include the next batch.  Output must be contained in an inline markdown code block.
