# Keepedia Release Plan

## Releases

### v1.0 - Initial Release
- Movie ripping with OMDB
- Metadata admin UI
- Track selection (audio/subtitles)
- Extras support with Plex naming
- Preview server for ripped files

### v1.1 - TMDB Migration
- Replace OMDB with TMDB
- Proxy endpoints in disc-api (`/search/movie`, `/search/tv`)
- No API key required for users
- Remove OMDB settings from settings page
- Remove `OMDB_API_KEY` from user model

### v1.2 - Media Server Notifications
- Settings: Configure Jellyfin/Plex URL + API token
- After encode → trigger library refresh via API
- Targeted scan (specific folder only)
- Support for Jellyfin + Plex

### v1.3 - Multi-disc Support
- Prompt "Main disc / Secondary disc" after movie identification
- Link secondary disc to main disc via IMDB ID
- `parent_checksum` + `disc_number` in database
- Extras from disc 2 → same folder with `[Disc 2]` prefix

### v1.4 - TV Series Support
- Series mode in script (minimal input: series name + season)
- Metadata admin UI for episode mapping
- Auto-match on duration
- Plex naming: `Show - S01E01 - Title.mkv`
- TMDB integration for episode data

### v1.5 - Multi-language Support
- Multi-language support for keepedia.org
- Swedish, English, + more languages
- Language selection in settings
- Translation of metadata admin UI
- Localized error messages in ripper script

---

## Future Features (backlog)

### keepedia.org

**"My Discs" Redesign - Video Store Theme**
- Retro video store vibe
- Views: Shelf view, List view, Detail view
- Sorting: Genre, Year, Format, A-Z
- Filter by DVD/Blu-ray/4K
- "New Arrivals" and "Staff Picks" sections

**3D Cases**
- Cover wraps around front + spine
- Hover → rotate and show spine
- Click → open case (animation)
- Different thickness for DVD/Blu-ray/Box-set
- Glossy plastic effect

**Physical Shelf Organizer**
- Define your shelf (slots, shelves)
- Generate placement guide based on sorting
- Print labels for shelf slots
- "Where should I put this?" - suggestions for new disc
- Visualization of physical shelf with covers

---

### Jellyfin/Plex Plugin

**Keepedia Collection Plugin**
- Display ripped discs as physical cases
- DVD/Blu-ray/4K badges
- Multi-disc boxes as box-set
- Clear extras section with categories
- Show which disc each extra comes from
- Link to keepedia.org for more info
- Publish in plugin marketplace

---

### Ripping Station

**Bootable USB Image**
- Minimal Linux (Debian/Ubuntu LTS)
- Pre-installed: MakeMKV, HandBrake, mkvtoolnix
- Sleek GUI (Electron/Qt/Web)
- Auto-detect DVD/Blu-ray drive
- WiFi setup wizard
- Download .iso from keepedia.org

**Media Server Auto-detect**
- Find Jellyfin/Plex on network automatically
- Suggest library paths
- One-click configuration
