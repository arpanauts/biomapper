# Task: Uncomment Mapping Paths in protein_config.yaml

## Context:
The `GenericFileLookupClient` has been implemented and relevant `mapping_clients` sections in `/home/ubuntu/biomapper/configs/protein_config.yaml` that depend on this client (or were previously commented out for other reasons but are now believed to be ready) have been uncommented.

The next step is to uncomment the `mapping_paths` that utilize these now-active clients to enable full end-to-end testing of the database population script.

## Instructions:
1.  **Open and Edit `protein_config.yaml`:**
    *   File path: `/home/ubuntu/biomapper/configs/protein_config.yaml`

2.  **Identify and Uncomment Mapping Paths:**
    *   Locate the `mapping_paths:` section at the end of the file.
    *   Uncomment the following specific mapping paths by removing the leading `#` and space from each line of their definitions:
        *   `ARIVALE_TO_UKBB_VIA_UNIPROT` (approximately lines 359-367 in its commented state)
        *   `UKBB_TO_ARIVALE_VIA_UNIPROT` (approximately lines 369-377 in its commented state)

    *   **Target Content to Uncomment (Example for ARIVALE_TO_UKBB_VIA_UNIPROT):**
        ```yaml
        #  - name: "ARIVALE_TO_UKBB_VIA_UNIPROT"
        #    source_type: "ARIVALE_PROTEIN_ID_ONTOLOGY"
        #    target_type: "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
        #    priority: 1
        #    steps:
        #      - resource: "arivale_protein_to_uniprot_lookup"
        #        order: 1
        #      - resource: "uniprot_to_ukbb_assay_lookup"
        #        order: 2
        ```
    *   **Expected Uncommented Content (Example for ARIVALE_TO_UKBB_VIA_UNIPROT):**
        ```yaml
          - name: "ARIVALE_TO_UKBB_VIA_UNIPROT"
            source_type: "ARIVALE_PROTEIN_ID_ONTOLOGY"
            target_type: "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
            priority: 1
            steps:
              - resource: "arivale_protein_to_uniprot_lookup"
                order: 1
              - resource: "uniprot_to_ukbb_assay_lookup"
                order: 2
        ```
    *   Carefully ensure correct indentation when uncommenting.

3.  **Review Other Commented Paths:**
    *   Examine any other commented-out paths in the `mapping_paths:` section. If their constituent resources (clients) are now believed to be active and correctly configured (e.g., `ukbb_uniprot_identity_lookup` if an identity client for UKBB UniProt was intended and is available, or paths involving SPOKE/KG2 clients), uncomment them as well. Use your best judgment based on the client names.
    *   If unsure about a path or its resources, leave it commented.

4.  **Save the changes** to `/home/ubuntu/biomapper/configs/protein_config.yaml`.

## Expected Output:
*   The `/home/ubuntu/biomapper/configs/protein_config.yaml` file with the specified `mapping_paths` (and any other confidently ready paths) uncommented.

## Feedback Requirements:
Create a Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-uncomment-mapping-paths.md` (use the current UTC timestamp) in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory.
In this feedback file, please:
1.  Confirm that the specified mapping paths were uncommented.
2.  List any additional mapping paths that were uncommented, along with a brief justification.
3.  Note any mapping paths that were left commented and why (if applicable).
