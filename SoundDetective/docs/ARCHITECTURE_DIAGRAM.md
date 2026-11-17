# Sound Detective Architecture Diagram

## Application Architecture

The desktop app guides a player from case selection through sound editing and submission. Game sessions own challenge rules and progress; preview workers render audio through the local SuperCollider tools; saves stay on the player's computer.

```mermaid
flowchart TD
    APlayer["Player"]
    ALauncher["Python application launcher"]
    AStudio["Qt studio and case board"]
    APanel["Timbre and Wordle panels"]
    AGame["Game sessions and scoring"]
    AContent["Case content files"]
    APreview["Background audio preview"]
    ASC["Local SuperCollider renderer"]
    APlayback["Audio playback"]
    ASaves["Local JSON progress"]

    APlayer -->|"starts and controls"| ALauncher
    ALauncher -->|"opens"| AStudio
    AStudio -->|"selects and hosts"| APanel
    APanel -->|"submits edits to"| AGame
    AGame -->|"loads targets from"| AContent
    AGame -->|"saves progress through"| ASaves
    APanel -->|"requests a preview from"| APreview
    APreview -->|"renders with"| ASC
    ASC -->|"returns a WAV to"| APreview
    APreview -->|"provides sound to"| APlayback
    APlayback -->|"plays for"| APlayer
    AGame -->|"returns scores and hints to"| APanel
```

### Technology Stack Summary

| Area | Technology | Role |
| --- | --- | --- |
| Application | Python 3.11 | Game logic and desktop application |
| User interface | PySide6 6.8.3 | Qt windows, controls, and audio playback |
| Audio rendering | SuperCollider (`sclang`, `scsynth`) | Synthesizes the game's sounds locally |
| Audio processing | NumPy, SciPy, librosa, SoundFile | Sound comparison, analysis, and WAV handling |
| Progress storage | JSON files | Stores local case progress and preferences |

## Data Architecture

Case definitions are read from the project's content files. A game session evaluates submissions and produces scores, hints, and progress. Progress and preferences are saved as JSON in the local `userdata` folder; audio previews use temporary runtime files and can be recreated.

## Key Decisions

- Sound synthesis runs locally through SuperCollider; the game does not require a remote audio service.
- Preview rendering runs in the background so the interface can remain responsive and can discard results from replaced requests.
- Case content, game rules, audio rendering, and saved player progress are kept in separate parts of the project.

## Component Relationships

```mermaid
flowchart LR
    subgraph CInterface["Desktop interface"]
        CStudio["Studio"]
        CBoard["Case board"]
        CPanels["Case panels"]
        CFeedback["Scores and hints"]
        CStudio -->|"opens"| CBoard
        CBoard -->|"hosts selected case"| CPanels
        CPanels -->|"shows"| CFeedback
    end

    subgraph CGame["Game logic"]
        CSessions["Case sessions"]
        CTimbre["Timbre cases T01 to T09"]
        CWordle["Sound Wordle W01 to W09"]
        CProgress["Progress and scoring"]
        CTimbre -->|"uses"| CSessions
        CWordle -->|"uses"| CSessions
        CSessions -->|"updates"| CProgress
    end

    subgraph CAudio["Audio"]
        CPreview["Preview workers"]
        CRenderer["SuperCollider renderer"]
        CPlayback["Playback"]
        CPreview -->|"requests synthesis from"| CRenderer
        CRenderer -->|"returns WAV audio to"| CPreview
        CPreview -->|"sends audio to"| CPlayback
    end

    subgraph CFiles["Local files"]
        CContent["Case content"]
        CSaves["JSON saves"]
    end

    CPanels -->|"submits to"| CSessions
    CFeedback -->|"comes from"| CProgress
    CPanels -->|"requests sound from"| CPreview
    CSessions -->|"loads cases from"| CContent
    CProgress -->|"is saved in"| CSaves
```

### Component Inventory

| Component | Responsibility |
| --- | --- |
| Studio and case board | Presents the game and routes the player to a selected case |
| Timbre and Wordle panels | Let the player listen, edit sound parameters, preview, and submit |
| Game sessions | Apply each case's rules and track submissions |
| Progress and scoring | Produces feedback, hints, and saved progress |
| Preview workers | Render requested sounds without blocking the interface |
| SuperCollider renderer | Synthesizes audio locally |
| Local files | Provide case definitions and retain player progress |
