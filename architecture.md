# Patient Action Guide — Detailed Architectural Diagram

```mermaid
flowchart TD
    %% Styling Classes
    classDef inputNode fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1
    classDef processNode fill:#F3E5F5,stroke:#6A1B9A,stroke-width:2px,color:#4A148C
    classDef aiNode fill:#FFF8E1,stroke:#FF8F00,stroke-width:2px,color:#E65100
    classDef outputNode fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20
    classDef databaseNode fill:#ECEFF1,stroke:#455A64,stroke-width:2px,color:#263238

    %% 1. User Input Layer
    subgraph Input ["User Interface (Streamlit)"]
        A((Patient UI)):::inputNode -->|1. Set Age, Gender, Language| B[App Session State]:::inputNode
        A -->|2. Upload Medical File| C{File Extension Check}:::inputNode
    end

    %% 2. Processing Layer
    subgraph Extraction ["Document Processing Pipeline (extractor.py)"]
        C -->|Valid Image\n[PNG, JPG]| D[Extract Raw Byte Stream]:::processNode
        C -->|Valid Document\n[PDF]| E[PyMuPDF Multi-page Scan]:::processNode
        E -->|Render 150 DPI Image| F[Convert All Pages to JPEG Bytes]:::processNode
    end

    %% 3. Pre-Analysis Routing
    subgraph Routing ["Agent Routing Logic (agent.py)"]
        D --> G{Gemini Tool Selector}:::processNode
        F --> G
        G -->|Visual Image Selected| H[Tool: analyze_visual_document]:::processNode
        G -->|Typed PDF Selected| I[Tool: analyze_text_document]:::processNode
    end

    %% 4. AI Engine Layer
    subgraph Agent ["Gemini 2.5 Flash Native Processing"]
        J[(config.py MEDICAL_KNOWLEDGE\n12 Indian Condition Categories)]:::databaseNode -.-> K
        H --> K[Builder System Prompt Compilation]:::aiNode
        I --> K
        K --> L((Gemini 2.5 Flash Miltimodal AI)):::aiNode
        L -->|Applies Response Schema| M[Strict JSON Extraction]:::aiNode
        M --> N{validate_output Check}:::aiNode
        N -->|Fails Schema| O[Resubmit Prompt 1x]:::aiNode
        O --> L
    end

    %% 5. Output Construction Layer
    subgraph Output ["Dashboard Rendering (output_view.py)"]
        N -->|Passes Schema| P[Decode Action Plan Dictionary]:::outputNode
        P --> Q[Generate Color-Coded Health Status]:::outputNode
        P --> R[Calculate Age Context & Doctor Rule]:::outputNode
        P --> S[Generate Ayurveda & Cost Guard Specs]:::outputNode
        P --> T[Calculate Irreversible Timeline Warning]:::outputNode
        
        Q --> Final[Render Streamlit User Dashboard]:::outputNode
        R --> Final
        S --> Final
        T --> Final
        
        Final --> U[Generate .txt File Download]:::outputNode
    end
```
