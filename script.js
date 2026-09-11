/* =====================================================
   API
===================================================== */

const API_URL = "http://127.0.0.1:8000";

const albumById = new Map(
    albums.map(album => [album.id, album])
);

let artistDirectoryCache = null;

let persistTimer = null;

let searchTimer = null;


function coverSrc(url, size = 250) {

    if (!url) {

        return "";

    }

    return url.replace(
        /\/\d+x\d+-/,
        `/${size}x${size}-`
    );

}


function artistPhotoSrc(name, size = 250) {

    const photos =
        typeof artistPhotos === "undefined"
        ? {}
        : artistPhotos;

    const url =
        photos[name] || "";

    if (url) {

        return coverSrc(url, size);

    }

    return "";

}


async function apiFetch(url, options = {}, timeoutMs = 2500) {

    const controller =
        new AbortController();

    const timer =
        setTimeout(
            () => controller.abort(),
            timeoutMs
        );

    try {

        return await fetch(
            url,
            {
                ...options,
                signal: controller.signal
            }
        );

    } finally {

        clearTimeout(timer);

    }

}


/* =====================================================
   APPLICATION STATE
===================================================== */

let currentAlbum = null;

let currentSongIndex = 0;

let currentRating = 5.0;

let isDraggingDial = false;

let isDraggingSongLine = false;

let songLinePercent = null;

let dialWasMoved = false;

let pendingSongScroll = false;


/*
    IMPORTANT:

    Guest ratings are ONLY stored here.

    They are NOT saved to localStorage.

    Refreshing the page destroys them.
*/

let guestRatings = {};


/*
    Logged-in user information.
*/

let currentUser = null;

let albumReturnTo = "home";

let currentArtistName = null;

let albumSort =
    localStorage.getItem("albumSort") || "latest";

let artistSort =
    localStorage.getItem("artistSort") || "highest";

const ALBUM_SORT_LABELS = {
    latest: "Latest",
    new: "New",
    year: "By year",
    highest: "Highest yours",
    lowest: "Lowest yours",
    "highest-global": "Highest global",
    "lowest-global": "Lowest global"
};

const ARTIST_SORT_LABELS = {
    az: "A–Z",
    za: "Z–A",
    highest: "Highest yours",
    lowest: "Lowest yours",
    "highest-global": "Highest global",
    "lowest-global": "Lowest global",
    "highest-friends": "Highest friends",
    "lowest-friends": "Lowest friends",
    albums: "Most albums",
    latest: "Latest release"
};


/* =====================================================
   INITIALIZE
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        renderAlbums();

        setupDial();

        setupSongRater();

        setupStickyRatingChrome();

        updateRatingColor();

        setActiveNav("navHome");

        updateSortButton();

        updateArtistSortButton();

        document.addEventListener(
            "click",
            event => {

                const wrap =
                    document.getElementById(
                        "albumSortWrap"
                    );


                const artistWrap =
                    document.getElementById(
                        "artistSortWrap"
                    );


                if (
                    wrap &&
                    !wrap.contains(event.target)
                ) {

                    document
                        .getElementById(
                            "sortOptions"
                        )
                        .classList.add("hidden");

                }


                if (
                    artistWrap &&
                    !artistWrap.contains(event.target)
                ) {

                    document
                        .getElementById(
                            "artistSortOptions"
                        )
                        .classList.add("hidden");

                }

            }
        );

        await checkLogin();

        window.addEventListener(
            "pagehide",
            () => persistAccountRatings(true)
        );

        if ("serviceWorker" in navigator) {

            navigator.serviceWorker.register("sw.js");

        }

    }
);


/* =====================================================
   CHECK LOGIN
===================================================== */

async function checkLogin() {

    const token =
        localStorage.getItem("ratedToken");


    if (!token) {

        updateProfileButton();

        return;

    }


    if (token.startsWith("local-")) {

        restoreLocalSession();

        return;

    }


    try {

        const response =
            await apiFetch(
                `${API_URL}/me`,
                {
                    headers: {
                        Authorization:
                            `Bearer ${token}`
                    }
                }
            );


        if (!response.ok) {

            if (!restoreLocalSession()) {

                localStorage.removeItem(
                    "ratedToken"
                );

            }

            updateProfileButton();

            return;

        }


        currentUser =
            await response.json();


        localStorage.setItem(
            "ratedUser",
            JSON.stringify(currentUser)
        );


        updateProfileButton();


        await loadUserRatings();


    } catch (error) {

        console.error(
            "Could not connect to backend:",
            error
        );

        restoreLocalSession();

        updateProfileButton();

    }

}


/* =====================================================
   PAGE MANAGEMENT
===================================================== */

function hideAllPages() {

    document
        .querySelectorAll(".page")
        .forEach(page => {

            page.classList.add("hidden");

        });

}


function setActiveNav(activeId) {

    document
        .querySelectorAll(".nav-button, .tab-button")
        .forEach(button => {

            button.classList.remove("active");

        });


    if (!activeId) {

        return;

    }


    const button =
        document.getElementById(
            activeId
        );


    if (button) {

        button.classList.add("active");

    }


    const tabMap = {
        navHome: "tabHome",
        navArtists: "tabArtists",
        navSaved: "tabSaved",
        navPerfect: "tabPerfect",
        navFriends: "tabFriends"
    };


    const tab =
        document.getElementById(
            tabMap[activeId]
        );


    if (tab) {

        tab.classList.add("active");

    }

}


function showHome() {

    hideAllPages();

    setActiveNav("navHome");

    document
        .getElementById("homePage")
        .classList.remove("hidden");

    renderAlbums();

}


function showSaved() {

    if (!currentUser) {

        openAuth();

        return;

    }


    hideAllPages();

    setActiveNav("navSaved");

    document
        .getElementById("savedPage")
        .classList.remove("hidden");

    renderSaved();

}


function handleProtectedPage(page) {

    if (page === "saved") {

        showSaved();

    }

}


function showPerfectAlbums() {

    hideAllPages();

    setActiveNav("navPerfect");

    document
        .getElementById("perfectPage")
        .classList.remove("hidden");

    renderPerfect();

}


function showFriends() {

    if (!currentUser) {

        openAuth();

        return;

    }


    hideAllPages();

    setActiveNav("navFriends");

    document
        .getElementById("friendsPage")
        .classList.remove("hidden");

}


function showArtists() {

    hideAllPages();

    setActiveNav("navArtists");

    currentArtistName = null;

    document
        .getElementById("artistsPage")
        .classList.remove("hidden");

    renderArtists();

    updateArtistSortButton();

}


function goBackFromAlbum() {

    if (
        albumReturnTo === "artist"
        &&
        currentArtistName
    ) {

        openArtist(currentArtistName);

        return;

    }


    showHome();

}


function splitArtistNames(artist) {

    return artist
        .split(/\s+&\s+/)
        .map(name => name.trim())
        .filter(name => name.length > 0);

}


function getArtistDirectory() {

    if (artistDirectoryCache) {

        return artistDirectoryCache;

    }


    const directory = {};


    albums.forEach(album => {

        splitArtistNames(album.artist)
            .forEach(name => {

                if (!directory[name]) {

                    directory[name] = {
                        name,
                        albums: []
                    };

                }

                directory[name].albums.push(
                    album
                );

            });

    });


    artistDirectoryCache =
        Object
            .values(directory)
            .sort(
                (a, b) =>
                    a.name.localeCompare(
                        b.name
                    )
            );

    return artistDirectoryCache;

}


function getArtistAverage(artistAlbums) {

    return averageScores(
        artistAlbums.map(album =>
            getAlbumRating(album.id)
        )
    );

}


function getArtistFriendsAverage(artistAlbums) {

    return averageScores(
        artistAlbums.map(album =>
            getAlbumFriendsRating(album.id)
        )
    );

}


function getArtistGlobalAverage(artistAlbums) {

    return averageScores(
        artistAlbums.map(album =>
            getAlbumGlobalRating(album.id)
        )
    );

}


function getAlbumFriendsRating(albumId) {

    return null;

}


function getAlbumGlobalRating(albumId) {

    if (typeof globalRatings === "undefined") {

        return null;

    }


    const entry =
        globalRatings[albumId]
        ||
        globalRatings[String(albumId)];


    if (entry == null) {

        return null;

    }


    if (typeof entry === "number") {

        return entry;

    }


    if (
        typeof entry.score === "number"
    ) {

        return entry.score;

    }


    return null;

}


function seededUnit(seed) {

    let t = seed | 0;

    t = Math.imul(t ^ (t >>> 15), t | 1);

    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);

    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;

}


function getSongGlobalRating(albumId, songIndex) {

    const albumScore =
        getAlbumGlobalRating(albumId);


    if (albumScore === null) {

        return null;

    }


    const unit =
        seededUnit(
            albumId * 131 +
            songIndex * 17 +
            29
        );


    const score =
        Math.round(
            Math.min(
                10,
                Math.max(
                    0,
                    albumScore + (unit - 0.5) * 1.2
                )
            ) * 10
        ) / 10;


    return score;

}


function albumHasUserRatings(albumId) {

    const ratings =
        guestRatings[albumId];


    if (!ratings) {

        return false;

    }


    return Object.keys(ratings).length > 0;

}


function averageScores(values) {

    const scores =
        values.filter(score =>
            score !== null
            &&
            score !== undefined
        );


    if (scores.length === 0) {

        return null;

    }


    const average =
        scores.reduce(
            (sum, score) =>
                sum + score,
            0
        ) / scores.length;


    return Math.round(
        average * 10
    ) / 10;

}


function compareNullableScores(left, right, descending, tiebreak) {

    if (left === null && right === null) {

        return tiebreak();

    }


    if (left === null) {

        return 1;

    }


    if (right === null) {

        return -1;

    }


    const diff =
        descending
        ? right - left
        : left - right;


    return diff || tiebreak();

}


function artistScoreMarkup(score) {

    if (score === null) {

        return "—";

    }


    return score.toFixed(1);

}


function createArtistCover(artist) {

    const src =
        artistPhotoSrc(artist.name)
        ||
        coverSrc(
            (artist.albums[0] || {}).cover
        );


    return `

        <img
            class="artist-photo"
            src="${src}"
            alt="${artist.name}"
            loading="lazy"
            decoding="async"
            width="64"
            height="64"
        >

    `;

}


function createArtistCard(artist, listNumber) {

    const yourAverage =
        getArtistAverage(
            artist.albums
        );


    const friendsAverage =
        getArtistFriendsAverage(
            artist.albums
        );


    const globalAverage =
        getArtistGlobalAverage(
            artist.albums
        );


    const ratedCount =
        artist.albums.filter(
            album =>
                getAlbumRating(
                    album.id
                ) !== null
        ).length;


    return `

        <div
            class="album-card artist-card"
            onclick="openArtist('${encodeURIComponent(artist.name)}')"
        >

            <div class="album-number">
                ${listNumber}
            </div>


            ${createArtistCover(artist)}


            <div class="album-information">

                <h3>
                    ${artist.name}
                </h3>

                <p>
                    ${artist.albums.length}
                    album${artist.albums.length === 1 ? "" : "s"}
                    ·
                    ${ratedCount}
                    rated
                </p>

            </div>


            <div class="score-triple">

                <div class="score-column">

                    <span class="score-label">
                        YOUR AVG
                    </span>

                    <span
                        class="score user-score"
                        ${
                            yourAverage !== null
                            ? `style="${scoreColorStyle(yourAverage)}"`
                            : ""
                        }
                    >

                        ${artistScoreMarkup(yourAverage)}

                    </span>

                </div>


                <div class="score-column">

                    <span class="score-label">
                        FRIENDS
                    </span>

                    <span
                        class="score friend-score"
                        ${
                            friendsAverage !== null
                            ? `style="${scoreColorStyle(friendsAverage)}"`
                            : ""
                        }
                    >

                        ${artistScoreMarkup(friendsAverage)}

                    </span>

                </div>


                <div class="score-column">

                    <span class="score-label">
                        GLOBAL
                    </span>

                    <span
                        class="score global-score"
                        ${
                            globalAverage !== null
                            ? `style="${scoreColorStyle(globalAverage)}"`
                            : ""
                        }
                    >

                        ${artistScoreMarkup(globalAverage)}

                    </span>

                </div>

            </div>

        </div>

    `;

}


function sortArtistList(list) {

    const sorted = list.slice();

    const byName = (a, b) =>
        a.name.localeCompare(b.name);


    const newestYear = artist =>
        Math.max(
            ...artist.albums.map(album => album.year)
        );


    if (artistSort === "za") {

        sorted.sort(
            (a, b) =>
                b.name.localeCompare(a.name)
        );

    } else if (artistSort === "highest") {

        sorted.sort((a, b) =>
            compareNullableScores(
                getArtistAverage(a.albums),
                getArtistAverage(b.albums),
                true,
                () => byName(a, b)
            )
        );

    } else if (artistSort === "lowest") {

        sorted.sort((a, b) =>
            compareNullableScores(
                getArtistAverage(a.albums),
                getArtistAverage(b.albums),
                false,
                () => byName(a, b)
            )
        );

    } else if (artistSort === "highest-global") {

        sorted.sort((a, b) =>
            compareNullableScores(
                getArtistGlobalAverage(a.albums),
                getArtistGlobalAverage(b.albums),
                true,
                () => byName(a, b)
            )
        );

    } else if (artistSort === "lowest-global") {

        sorted.sort((a, b) =>
            compareNullableScores(
                getArtistGlobalAverage(a.albums),
                getArtistGlobalAverage(b.albums),
                false,
                () => byName(a, b)
            )
        );

    } else if (artistSort === "highest-friends") {

        sorted.sort((a, b) =>
            compareNullableScores(
                getArtistFriendsAverage(a.albums),
                getArtistFriendsAverage(b.albums),
                true,
                () => byName(a, b)
            )
        );

    } else if (artistSort === "lowest-friends") {

        sorted.sort((a, b) =>
            compareNullableScores(
                getArtistFriendsAverage(a.albums),
                getArtistFriendsAverage(b.albums),
                false,
                () => byName(a, b)
            )
        );

    } else if (artistSort === "albums") {

        sorted.sort(
            (a, b) =>
                b.albums.length - a.albums.length
                ||
                byName(a, b)
        );

    } else if (artistSort === "latest") {

        sorted.sort(
            (a, b) =>
                newestYear(b) - newestYear(a)
                ||
                byName(a, b)
        );

    } else {

        sorted.sort(byName);

    }

    return sorted;

}


function renderArtists(list) {

    const container =
        document.getElementById(
            "artistsList"
        );


    const artists =
        sortArtistList(
            list || getArtistDirectory()
        );


    container.innerHTML = "";


    if (artists.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                No artists found.

            </div>

        `;

        return;

    }


    container.innerHTML =
        artists
            .map((artist, index) =>
                createArtistCard(
                    artist,
                    index + 1
                )
            )
            .join("");

}


function openArtistFromEvent(event) {

    event.stopPropagation();


    const name =
        decodeURIComponent(
            event.currentTarget.dataset.artist
        );


    openArtist(name);

}


function openArtist(artistName) {

    const name =
        decodeURIComponent(artistName);


    const artist =
        getArtistDirectory().find(
            item =>
                item.name === name
        );


    if (!artist) {

        return;

    }


    currentArtistName = artist.name;


    hideAllPages();

    setActiveNav("navArtists");

    document
        .getElementById("artistPage")
        .classList.remove("hidden");


    const average =
        getArtistAverage(
            artist.albums
        );


    const friendsAverage =
        getArtistFriendsAverage(
            artist.albums
        );


    const globalAverage =
        getArtistGlobalAverage(
            artist.albums
        );


    const ratedCount =
        artist.albums.filter(
            album =>
                getAlbumRating(
                    album.id
                ) !== null
        ).length;


    document.getElementById(
        "artistHero"
    ).innerHTML = `

        <div class="artist-hero">

            <div class="artist-hero-photo">

                <img
                    class="artist-hero-cover"
                    src="${
                        artistPhotoSrc(artist.name, 500)
                        ||
                        coverSrc(artist.albums[0].cover, 500)
                    }"
                    alt="${artist.name}"
                >

            </div>


            <div class="album-details">

                <p class="eyebrow">
                    ARTIST
                </p>


                <h1>
                    ${artist.name}
                </h1>


                <p class="album-meta">

                    ${artist.albums.length}
                    album${artist.albums.length === 1 ? "" : "s"}

                    ·

                    ${ratedCount}
                    rated

                </p>


                <div class="album-stat-row">


                    <div class="album-stat">

                        <span class="small-label">
                            YOUR AVERAGE
                        </span>

                        <strong
                            ${
                                average !== null
                                ? `style="${scoreColorStyle(average)}"`
                                : ""
                            }
                        >

                            ${artistScoreMarkup(average)}

                        </strong>

                    </div>


                    <div class="album-stat">

                        <span class="small-label">
                            FRIENDS
                        </span>

                        <strong
                            ${
                                friendsAverage !== null
                                ? `style="${scoreColorStyle(friendsAverage)}"`
                                : ""
                            }
                        >

                            ${artistScoreMarkup(friendsAverage)}

                        </strong>

                    </div>


                    <div class="album-stat">

                        <span class="small-label">
                            GLOBAL
                        </span>

                        <strong
                            ${
                                globalAverage !== null
                                ? `style="${scoreColorStyle(globalAverage)}"`
                                : ""
                            }
                        >

                            ${artistScoreMarkup(globalAverage)}

                        </strong>

                    </div>


                </div>

            </div>

        </div>

    `;


    const albumsContainer =
        document.getElementById(
            "artistAlbums"
        );


    albumsContainer.innerHTML =
        sortAlbumList(artist.albums)
            .map((album, index) =>
                createAlbumCard(
                    album,
                    true,
                    index + 1
                )
            )
            .join("");

}


/* =====================================================
   PROFILE BUTTON
===================================================== */

function updateProfileButton() {

    const button =
        document.getElementById(
            "profileButton"
        );


    if (!currentUser) {

        button.textContent = "Login";

        return;

    }


    button.textContent =
        currentUser.username;

}


/* =====================================================
   ALBUM CARD
===================================================== */

function createAlbumCard(album, fromArtist = false, rank = null) {

    const rating =
        getAlbumRating(album.id);


    const globalRating =
        getAlbumGlobalRating(album.id);


    const artistLinks =
        splitArtistNames(album.artist)
            .map(name => `

                <span
                    class="artist-link"
                    data-artist="${encodeURIComponent(name)}"
                    onclick="openArtistFromEvent(event)"
                >
                    ${name}
                </span>

            `)
            .join(" & ");


    return `

        <div
            class="album-card"
            onclick="openAlbum(${album.id}, ${fromArtist})"
        >

            <div class="album-number">
                ${rank === null ? album.id : rank}
            </div>


            <img
                class="album-cover-small"
                src="${coverSrc(album.cover)}"
                alt="${album.title}"
                loading="lazy"
                decoding="async"
                width="64"
                height="64"
            >


            <div class="album-information">

                <h3>
                    ${album.title}
                </h3>

                <p>
                    ${artistLinks}
                    ·
                    ${album.year}
                </p>

            </div>


            <div class="score-column">

                <span class="score-label">
                    YOUR SCORE
                </span>

                <span
                    class="score user-score"
                    ${
                        rating !== null
                        ? `style="${scoreColorStyle(rating)}"`
                        : ""
                    }
                >

                    ${
                        rating !== null
                        ? rating.toFixed(1)
                        : "—"
                    }

                </span>

            </div>


            <div class="score-column">

                <span class="score-label">
                    FRIENDS
                </span>

                <span class="score friend-score">
                    —
                </span>

            </div>


            <div class="score-column">

                <span class="score-label">
                    GLOBAL
                </span>

                <span
                    class="score global-score"
                    ${
                        globalRating !== null
                        ? `style="${scoreColorStyle(globalRating)}"`
                        : ""
                    }
                >

                    ${
                        globalRating !== null
                        ? globalRating.toFixed(1)
                        : "—"
                    }

                </span>

            </div>

        </div>

    `;

}


/* =====================================================
   RENDER ALBUMS
===================================================== */

function renderAlbums(list = albums) {

    const container =
        document.getElementById(
            "albumGrid"
        );


    const sorted =
        sortAlbumList(list);


    container.innerHTML = "";


    if (sorted.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                No albums found.

            </div>

        `;

        return;

    }


    container.innerHTML =
        sorted
            .map((album, index) =>
                createAlbumCard(album, false, index + 1)
            )
            .join("");

}


function compareAlbumScores(list, getScore, direction) {

    const sorted = list.slice();

    sorted.sort((a, b) => {

        const left = getScore(a);
        const right = getScore(b);

        if (left === null && right === null) {
            return b.year - a.year;
        }

        if (left === null) {
            return 1;
        }

        if (right === null) {
            return -1;
        }

        return direction === "asc"
            ? left - right
            : right - left;

    });

    return sorted;

}


function sortAlbumList(list) {

    if (albumSort === "new") {

        return list.slice().sort(
            (a, b) => b.id - a.id
        );

    }

    if (albumSort === "year") {

        return list.slice().sort(
            (a, b) =>
                a.year - b.year ||
                a.id - b.id
        );

    }

    if (albumSort === "highest") {

        return compareAlbumScores(
            list,
            album => getAlbumRating(album.id),
            "desc"
        );

    }

    if (albumSort === "lowest") {

        return compareAlbumScores(
            list,
            album => getAlbumRating(album.id),
            "asc"
        );

    }

    if (albumSort === "highest-global") {

        return compareAlbumScores(
            list,
            album => getAlbumGlobalRating(album.id),
            "desc"
        );

    }

    if (albumSort === "lowest-global") {

        return compareAlbumScores(
            list,
            album => getAlbumGlobalRating(album.id),
            "asc"
        );

    }

    return list.slice().sort(
        (a, b) =>
            b.year - a.year ||
            b.id - a.id
    );

}


function toggleSortMenu(event) {

    if (event) {

        event.stopPropagation();

    }


    const menu =
        document.getElementById(
            "sortOptions"
        );


    menu.classList.toggle("hidden");


    document
        .getElementById("artistSortOptions")
        .classList.add("hidden");

}


function setAlbumSort(sort) {

    albumSort = sort;

    localStorage.setItem(
        "albumSort",
        sort
    );

    updateSortButton();

    document
        .getElementById("sortOptions")
        .classList.add("hidden");

    const query =
        document.getElementById(
            "searchInput"
        ).value.trim();

    if (query) {

        applySearch();

    } else {

        renderAlbums();

    }

}


function updateSortButton() {

    const label =
        document.getElementById(
            "sortLabel"
        );

    if (label) {

        label.textContent =
            ALBUM_SORT_LABELS[albumSort] ||
            "Latest";

    }


    document
        .querySelectorAll("#sortOptions .sort-option")
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.sort === albumSort
            );

        });

}


function toggleArtistSortMenu(event) {

    if (event) {

        event.stopPropagation();

    }


    document
        .getElementById("sortOptions")
        .classList.add("hidden");


    document
        .getElementById("artistSortOptions")
        .classList.toggle("hidden");

}


function setArtistSort(sort) {

    artistSort = sort;

    localStorage.setItem(
        "artistSort",
        sort
    );

    updateArtistSortButton();

    document
        .getElementById("artistSortOptions")
        .classList.add("hidden");


    const query =
        document.getElementById(
            "searchInput"
        ).value.trim();


    const artistsVisible =
        !document
            .getElementById("artistsPage")
            .classList.contains("hidden");


    if (query && artistsVisible) {

        applySearch();

    } else if (artistsVisible) {

        renderArtists();

    }

}


function updateArtistSortButton() {

    const label =
        document.getElementById(
            "artistSortLabel"
        );


    if (label) {

        label.textContent =
            ARTIST_SORT_LABELS[artistSort] ||
            "Highest yours";

    }


    document
        .querySelectorAll("#artistSortOptions .sort-option")
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.sort === artistSort
            );

        });

}


/* =====================================================
   OPEN ALBUM
===================================================== */

function openAlbum(albumId, fromArtist = false) {

    currentAlbum =
        albumById.get(albumId);


    currentSongIndex = 0;

    dialWasMoved = false;


    albumReturnTo =
        fromArtist
        ? "artist"
        : "home";


    const savedRating =
        getSongRating(
            albumId,
            0
        );


    if (savedRating !== null) {

        currentRating =
            savedRating;

    } else {

        currentRating = 5.0;

    }


    hideAllPages();


    document
        .getElementById("albumPage")
        .classList.remove("hidden");


    renderAlbumHero();

    renderSongs();

    updateDial();

    updateRatingActionButton();

    hideAlbumResult();

    syncStickyRatingChrome();

    pendingSongScroll = true;

    requestAnimationFrame(() => {

        requestAnimationFrame(
            () => scrollSelectedSongIntoView()
        );

    });

}


/* =====================================================
   GET SONG RATING
===================================================== */

function getSongRating(
    albumId,
    songIndex
) {

    const ratings =
        guestRatings[albumId];


    if (!ratings) {

        return null;

    }


    if (
        ratings[songIndex] === undefined
    ) {

        return null;

    }


    return ratings[songIndex];

}


/* =====================================================
   ALBUM HERO
===================================================== */

function renderAlbumHero() {

    const album =
        currentAlbum;


    const albumScore =
        getAlbumRating(
            album.id
        );


    const globalScore =
        getAlbumGlobalRating(
            album.id
        );


    document.getElementById(
        "albumHero"
    ).innerHTML = `

        <div class="album-hero">

            <img
                class="album-cover-large"
                src="${coverSrc(album.cover, 500)}"
                alt="${album.title}"
                decoding="async"
            >


            <div class="album-details">

                <p class="eyebrow">
                    ALBUM
                </p>


                <h1>
                    ${album.title}
                </h1>


                <p class="artist">
                    ${
                        splitArtistNames(album.artist)
                            .map(name => `
                                <span
                                    class="artist-link"
                                    data-artist="${encodeURIComponent(name)}"
                                    onclick="openArtistFromEvent(event)"
                                >
                                    ${name}
                                </span>
                            `)
                            .join(" & ")
                    }
                </p>


                <p class="album-meta">

                    ${album.year}

                    ·

                    ${album.genre}

                    ·

                    ${album.songs.length}
                    songs

                </p>


                <div class="album-stat-row">


                    <div class="album-stat">

                        <span class="small-label">
                            YOUR SCORE
                        </span>

                        <strong
                            id="heroUserScore"
                            ${
                                albumScore !== null
                                ? `style="${scoreColorStyle(albumScore)}"`
                                : ""
                            }
                        >

                            ${
                                albumScore !== null
                                ? albumScore.toFixed(1)
                                : "—"
                            }

                        </strong>

                    </div>


                    <div class="album-stat">

                        <span class="small-label">
                            FRIENDS
                        </span>

                        <strong>
                            —
                        </strong>

                    </div>


                    <div class="album-stat">

                        <span class="small-label">
                            GLOBAL
                        </span>

                        <strong
                            ${
                                globalScore !== null
                                ? `style="${scoreColorStyle(globalScore)}"`
                                : ""
                            }
                        >

                            ${
                                globalScore !== null
                                ? globalScore.toFixed(1)
                                : "—"
                            }

                        </strong>

                    </div>


                </div>

            </div>

        </div>

    `;


    document.getElementById(
        "currentAlbumScore"
    ).textContent =

        albumScore !== null
        ? albumScore.toFixed(1)
        : "—";


    updateLiveScoreDisplays();

}


/* =====================================================
   SONG LIST
===================================================== */

function renderSongs() {

    const container =
        document.getElementById(
            "songsList"
        );


    parkSongRater();

    container.innerHTML = "";


    const ratings =
        guestRatings[
            currentAlbum.id
        ] || {};


    container.innerHTML =
        currentAlbum.songs.map(
            (song, index) => {

            const rating =
                ratings[index];


            const globalRating =
                getSongGlobalRating(
                    currentAlbum.id,
                    index
                );


            return `

                <div
                    class="song-item ${index === currentSongIndex ? "is-current" : ""}"
                    data-index="${index}"
                >

                <div
                    class="song-row ${index === currentSongIndex ? "current" : ""}"
                    data-index="${index}"
                    onclick="selectSong(${index})"
                >

                    <div class="song-name">

                        <span class="track-number">
                            ${index + 1}
                        </span>

                        <span class="play-icon">
                            ▶
                        </span>

                        <span class="song-title">
                            ${song}
                        </span>

                        <span class="rating-badge">
                            RATING
                        </span>

                    </div>


                    <div
                        class="
                            song-score
                            song-score-user
                            ${
                                rating !== undefined
                                ? "active"
                                : ""
                            }
                        "
                        ${
                            rating !== undefined
                            ? `style="${scoreColorStyle(rating)}"`
                            : ""
                        }
                    >

                        ${
                            rating !== undefined
                            ? rating.toFixed(1)
                            : "—"
                        }

                    </div>


                    <div class="song-score song-score-friends">
                        —
                    </div>


                    <div
                        class="
                            song-score
                            song-score-global
                            ${
                                globalRating !== null
                                ? "active"
                                : ""
                            }
                        "
                        ${
                            globalRating !== null
                            ? `style="${scoreColorStyle(globalRating)}"`
                            : ""
                        }
                    >

                        ${
                            globalRating !== null
                            ? globalRating.toFixed(1)
                            : "—"
                        }

                    </div>

                </div>

                </div>

            `;

            }
        ).join("");


    colorRatedSongScores();

    placeSongRater();

    updateResetAlbumButton();

}


function syncStickyRatingChrome() {

    const nav =
        document.querySelector(
            ".navbar"
        );


    const rating =
        document.querySelector(
            ".rating-section"
        );


    if (nav) {

        document
            .documentElement
            .style
            .setProperty(
                "--nav-height",
                `${nav.offsetHeight}px`
            );

    }


    if (rating && rating.offsetHeight) {

        document
            .documentElement
            .style
            .setProperty(
                "--rating-bar-height",
                `${rating.offsetHeight}px`
            );

    }

}


function setupStickyRatingChrome() {

    const nav =
        document.querySelector(
            ".navbar"
        );


    const rating =
        document.querySelector(
            ".rating-section"
        );


    if (!nav) {

        return;

    }


    syncStickyRatingChrome();

    new ResizeObserver(syncStickyRatingChrome).observe(nav);

    if (rating) {

        new ResizeObserver(syncStickyRatingChrome).observe(rating);

    }

}


function scrollSelectedSongIntoView(row) {

    const mobile =
        window.matchMedia(
            "(max-width: 1100px)"
        ).matches;


    const target =
        row
        ||
        document.querySelector(
            `.song-row[data-index="${currentSongIndex}"]`
        );


    if (!target) {

        return;

    }


    if (!mobile) {

        const rater =
            document.getElementById(
                "songRater"
            );


        const desktopTarget =
            (
                rater
                &&
                rater.offsetParent
            )
            ? rater
            : target;


        desktopTarget.scrollIntoView({
            block: "nearest",
            behavior: "smooth"
        });

        return;

    }


    const snap = () => {

        const song =
            document.querySelector(
                `.song-row[data-index="${currentSongIndex}"]`
            );


        if (!song) {

            return;

        }


        syncStickyRatingChrome();


        const nav =
            document.querySelector(
                ".navbar"
            );


        const sticky =
            document.querySelector(
                ".rating-section"
            );


        const targetTop =
            (nav ? nav.offsetHeight : 0)
            +
            (sticky ? sticky.offsetHeight : 0)
            +
            8;


        const delta =
            song.getBoundingClientRect().top -
            targetTop;


        if (Math.abs(delta) > 1) {

            window.scrollTo({
                top:
                    window.scrollY +
                    delta,
                behavior: "auto"
            });

        }

    };


    snap();

    requestAnimationFrame(snap);

    setTimeout(snap, 60);

    setTimeout(snap, 140);

}


function parkSongRater() {

    const rater =
        document.getElementById(
            "songRater"
        );


    const list =
        document.getElementById(
            "songsList"
        );


    if (rater && list) {

        list.after(rater);

    }

}


function placeSongRater() {

    const rater =
        document.getElementById(
            "songRater"
        );


    const item =
        document.querySelector(
            `.song-item[data-index="${currentSongIndex}"]`
        );


    if (!rater) {

        return;

    }


    if (item) {

        item.appendChild(rater);

    } else {

        parkSongRater();

    }

}


function setupSongRater() {

    const line =
        document.getElementById(
            "songRateLine"
        );


    const scale =
        document.getElementById(
            "songRateScale"
        );


    if (
        !line
        ||
        line.dataset.ready === "1"
    ) {

        return;

    }


    line.dataset.ready = "1";


    const startDrag = event => {

        if (
            event.pointerType === "mouse"
            &&
            event.button !== 0
        ) {

            return;

        }


        if (
            event.target.closest(
                ".song-rate-end"
            )
        ) {

            return;

        }


        const point =
            event.touches
            ? event.touches[0]
            : event;


        if (
            !point
            ||
            point.clientX === undefined
        ) {

            return;

        }


        event.preventDefault();

        event.stopPropagation();

        isDraggingSongLine = true;

        line.classList.add(
            "is-dragging"
        );


        try {

            (event.currentTarget || line)
                .setPointerCapture(
                    event.pointerId
                );

        } catch (error) {

        }


        setRatingFromLine(
            point,
            line
        );

    };


    const moveDrag = event => {

        if (!isDraggingSongLine) {

            return;

        }


        if (event.cancelable) {

            event.preventDefault();

        }


        const point =
            event.touches
            ? event.touches[0]
            : event.changedTouches
            ? event.changedTouches[0]
            : event;


        if (
            !point
            ||
            point.clientX === undefined
        ) {

            return;

        }


        setRatingFromLine(
            point,
            line
        );

    };


    const stopDrag = () => {

        if (!isDraggingSongLine) {

            return;

        }


        isDraggingSongLine = false;

        songLinePercent = null;

        line.classList.remove(
            "is-dragging"
        );


        persistLiveSongRating();

        persistAccountRatings(true);

        updateLiveScoreDisplays();

        updateInlineSongRater();

    };


    const surface =
        scale || line;


    surface.addEventListener(
        "pointerdown",
        startDrag
    );


    surface.addEventListener(
        "touchstart",
        startDrag,
        { passive: false }
    );


    document.addEventListener(
        "pointermove",
        moveDrag,
        { passive: false }
    );


    document.addEventListener(
        "touchmove",
        moveDrag,
        { passive: false }
    );


    document.addEventListener(
        "pointerup",
        stopDrag
    );


    document.addEventListener(
        "touchend",
        stopDrag
    );

}


function setSongRatingEnd(score) {

    currentRating = score;

    songLinePercent = null;

    dialWasMoved = true;

    updateDial();

    persistLiveSongRating();

    persistAccountRatings(true);

}


function setRatingFromLine(event, line) {

    const rect =
        line.getBoundingClientRect();


    const width =
        Math.max(rect.width, 1);


    const visualT =
        Math.max(
            0,
            Math.min(
                1,
                (event.clientX - rect.left) / width
            )
        );


    songLinePercent = visualT;


    const edge =
        Math.min(16, width * 0.05);


    const scoreT =
        Math.max(
            0,
            Math.min(
                1,
                (
                    event.clientX -
                    (rect.left + edge)
                )
                /
                Math.max(width - edge * 2, 1)
            )
        );


    currentRating =
        Math.round(
            (1 - scoreT) * 100
        ) / 10;


    dialWasMoved = true;


    updateDial();

}


function updateInlineSongRater() {

    const value =
        document.getElementById(
            "inlineRatingValue"
        );


    const dot =
        document.getElementById(
            "songRateDot"
        );


    if (value) {

        value.textContent =
            currentRating.toFixed(1);

    }


    if (dot) {

        dot.classList.add("visible");


        const percent =
            songLinePercent !== null
            ? songLinePercent * 100
            : (1 - currentRating / 10) * 100;


        dot.style.left =
            `${percent}%`;

    }

}


/* =====================================================
   SELECT SONG
===================================================== */

function selectSong(index) {

    currentSongIndex = index;


    const savedRating =
        getSongRating(
            currentAlbum.id,
            index
        );


    if (savedRating !== null) {

        currentRating =
            savedRating;

    } else {

        currentRating = 5.0;

    }


    dialWasMoved = false;

    pendingSongScroll = true;


    updateDial();

    updateRatingActionButton();

}


/* =====================================================
   DIAL
===================================================== */

function setupDial() {

    const dial =
        document.getElementById(
            "dial"
        );


    dial.addEventListener(
        "mousedown",
        event => {

            isDraggingDial = true;

            dial.classList.add("is-dragging");

            setRatingFromMouse(
                event
            );

        }
    );


    document.addEventListener(
        "mousemove",
        event => {

            if (!isDraggingDial) {

                return;

            }


            setRatingFromMouse(
                event
            );

        }
    );


    document.addEventListener(
        "mouseup",
        () => {

            isDraggingDial = false;

            dial.classList.remove("is-dragging");

        }
    );


    dial.addEventListener(
        "touchstart",
        event => {

            event.preventDefault();

            isDraggingDial = true;

            dial.classList.add("is-dragging");

            setRatingFromMouse(
                event.touches[0]
            );

        },
        {
            passive: false
        }
    );


    document.addEventListener(
        "touchmove",
        event => {

            if (!isDraggingDial) {

                return;

            }


            setRatingFromMouse(
                event.touches[0]
            );

        },
        {
            passive: false
        }
    );


    document.addEventListener(
        "touchend",
        () => {

            isDraggingDial = false;

            dial.classList.remove("is-dragging");

        }
    );


    dial.addEventListener(
        "wheel",
        event => {

            event.preventDefault();


            if (event.deltaY < 0) {

                currentRating += 0.1;

            } else {

                currentRating -= 0.1;

            }


            currentRating =
                Math.max(
                    0,
                    Math.min(
                        10,
                        currentRating
                    )
                );


            currentRating =
                Math.round(
                    currentRating * 10
                ) / 10;


            dialWasMoved = true;


            updateDial();

        },
        {
            passive: false
        }
    );

}


/* =====================================================
   DIAL CALCULATION
===================================================== */

function setRatingFromMouse(event) {

    const dial =
        document.getElementById(
            "dial"
        );


    const rect =
        dial.getBoundingClientRect();


    const centerX =
        rect.left +
        rect.width / 2;


    const centerY =
        rect.top +
        rect.height * (115 / 125);


    const x =
        event.clientX -
        centerX;


    const y =
        event.clientY -
        centerY;


    let angle =
        Math.atan2(
            y,
            x
        ) *
        180 /
        Math.PI;


    let score;


    if (angle > 0) {

        score =
            x < 0
            ? 0
            : 10;

    } else {

        score =
            ((angle + 180) / 180) * 10;

    }


    score =
        Math.max(
            0,
            Math.min(
                10,
                score
            )
        );


    currentRating =
        Math.round(
            score * 10
        ) / 10;


    dialWasMoved = true;


    updateDial();

}


/* =====================================================
   UPDATE DIAL
===================================================== */

function updateDial() {

    const value =
        document.getElementById(
            "ratingValue"
        );


    const dot =
        document.getElementById(
            "dialDot"
        );


    value.textContent =
        currentRating.toFixed(1);


    const angle =
        180 -
        (
            currentRating / 10
        ) *
        180;


    const radians =
        angle *
        Math.PI /
        180;


    const radius = 100;


    const x =
        115 +
        radius *
        Math.cos(radians);


    const y =
        115 -
        radius *
        Math.sin(radians);


    dot.style.left =
        `${x}px`;


    dot.style.top =
        `${y}px`;


    const arc =
        document.getElementById(
            "dialArc"
        );


    if (arc) {

        arc.style.strokeDashoffset =
            String(
                100 -
                currentRating * 10
            );

    }


    updateRatingColor();

    updateInlineSongRater();


    if (isDraggingSongLine) {

        writeLiveSongRating();

        updateResetAlbumButton();


        const cell =
            document.querySelector(
                `.song-row[data-index="${currentSongIndex}"] .song-score-user`
            );


        if (cell) {

            cell.textContent =
                currentRating.toFixed(1);

            cell.classList.add("active");

            applyScoreColor(
                cell,
                currentRating
            );

        }


        updateAlbumScoreChrome();

        return;

    }


    if (
        currentAlbum
        &&
        (
            dialWasMoved
            ||
            isDraggingDial
        )
    ) {

        persistLiveSongRating();

    }


    updateLiveScoreDisplays();

}


/* =====================================================
   RATING COLOR
===================================================== */

function ratingColorRGB(score) {

    const stops = [
        [255, 45, 45],
        [255, 148, 31],
        [231, 231, 43],
        [36, 216, 121],
        [40, 110, 255],
        [157, 53, 255],
        [255, 47, 146]
    ];


    const t =
        Math.max(
            0,
            Math.min(
                10,
                score
            )
        ) / 10;


    const position =
        t * (stops.length - 1);


    const index =
        Math.min(
            Math.floor(position),
            stops.length - 2
        );


    const blend =
        position - index;


    const start =
        stops[index];


    const end =
        stops[index + 1];


    return {
        r: Math.round(
            start[0] +
            (end[0] - start[0]) * blend
        ),
        g: Math.round(
            start[1] +
            (end[1] - start[1]) * blend
        ),
        b: Math.round(
            start[2] +
            (end[2] - start[2]) * blend
        )
    };

}


function ratingColorValue(score) {

    const {
        r,
        g,
        b
    } = ratingColorRGB(score);


    return `rgb(${r}, ${g}, ${b})`;

}


function ratingGlowValue(score) {

    const {
        r,
        g,
        b
    } = ratingColorRGB(score);


    return `0 0 10px rgba(${r}, ${g}, ${b}, 0.4)`;

}


function updateRatingColor() {

    [
        "ratingValue",
        "inlineRatingValue"
    ].forEach(id => {

        const element =
            document.getElementById(
                id
            );


        if (!element) {

            return;

        }


        element.style.color =
            ratingColorValue(
                currentRating
            );


        element.style.textShadow =
            ratingGlowValue(
                currentRating
            );

    });


    const arc =
        document.getElementById(
            "dialArc"
        );


    if (arc) {

        arc.style.stroke =
            ratingColorValue(
                currentRating
            );

    }

}


function writeLiveSongRating() {

    if (!currentAlbum) {

        return;

    }


    if (
        !guestRatings[
            currentAlbum.id
        ]
    ) {

        guestRatings[
            currentAlbum.id
        ] = {};

    }


    guestRatings[
        currentAlbum.id
    ][
        currentSongIndex
    ] = currentRating;

}


function persistLiveSongRating() {

    writeLiveSongRating();

    persistAccountRatings();

    updateResetAlbumButton();

}


function updateResetAlbumButton() {

    const hasRatings =
        currentAlbum
        &&
        albumHasUserRatings(
            currentAlbum.id
        );


    document
        .querySelectorAll(
            ".reset-album-button"
        )
        .forEach(button => {

            button.classList.toggle(
                "hidden",
                !hasRatings
            );

        });

}


async function resetAlbumRating() {

    if (!currentAlbum) {

        return;

    }


    if (
        !albumHasUserRatings(
            currentAlbum.id
        )
    ) {

        return;

    }


    const confirmed =
        window.confirm(
            "Clear all of your ratings for this album?"
        );


    if (!confirmed) {

        return;

    }


    delete guestRatings[
        currentAlbum.id
    ];


    persistAccountRatings(true);


    const token =
        localStorage.getItem(
            "ratedToken"
        );


    if (
        token
        &&
        !token.startsWith("local-")
    ) {

        try {

            await apiFetch(
                `${API_URL}/ratings/${currentAlbum.id}`,
                {
                    method: "DELETE",
                    headers: {
                        Authorization:
                            `Bearer ${token}`
                    }
                }
            );

        } catch (error) {

            console.error(error);

        }

    }


    currentSongIndex = 0;

    currentRating = 5.0;

    dialWasMoved = false;


    hideAlbumResult();

    renderAlbumHero();

    renderSongs();

    updateDial();

    updateRatingActionButton();

    updateResetAlbumButton();

    renderAlbums();

}


function persistAccountRatings(immediate) {

    if (!currentUser) {

        return;

    }

    const write = () => {

        localStorage.setItem(
            "ratedRatings_" + currentUser.id,
            JSON.stringify(guestRatings)
        );

    };

    if (immediate) {

        clearTimeout(persistTimer);

        write();

        return;

    }

    clearTimeout(persistTimer);

    persistTimer =
        setTimeout(write, 250);

}


function updateRainbowDot(score) {

    const dot =
        document.getElementById(
            "rainbowDot"
        );


    if (!dot) {

        return;

    }


    if (
        score === null
        ||
        score === undefined
    ) {

        dot.classList.remove("visible");

        return;

    }


    dot.classList.add("visible");


    const percent =
        (1 - score / 10) * 100;


    dot.style.left =
        `${percent}%`;

}


function colorRatedSongScores() {

    if (!currentAlbum) {

        return;

    }


    const ratings =
        guestRatings[
            currentAlbum.id
        ] || {};


    document
        .querySelectorAll(".song-row")
        .forEach(row => {

            const index =
                Number(
                    row.dataset.index
                );


            const cell =
                row.querySelector(
                    ".song-score-user"
                );


            const rating =
                ratings[index];


            if (
                cell
                &&
                rating !== undefined
            ) {

                applyScoreColor(
                    cell,
                    rating
                );

            }

        });

}


function updateCurrentSongScoreDisplay() {

    colorRatedSongScores();

    document
        .querySelectorAll(".song-item")
        .forEach(item => {

            item.classList.toggle(
                "is-current",
                Number(item.dataset.index) === currentSongIndex
            );

        });


    document
        .querySelectorAll(".song-row")
        .forEach(row => {

            row.classList.toggle(
                "current",
                Number(row.dataset.index) === currentSongIndex
            );

        });


    if (!currentAlbum) {

        return;

    }


    const row =
        document.querySelector(
            `.song-row[data-index="${currentSongIndex}"]`
        );


    if (!row) {

        return;

    }


    row.classList.add("current");

    placeSongRater();


    if (
        pendingSongScroll
        &&
        !isDraggingDial
        &&
        !isDraggingSongLine
    ) {

        pendingSongScroll = false;

        requestAnimationFrame(() => {

            requestAnimationFrame(
                () => scrollSelectedSongIntoView(row)
            );

        });

    }


    const cell =
        row.querySelector(
            ".song-score-user"
        );


    const showLive =
        dialWasMoved
        ||
        isDraggingDial
        ||
        isDraggingSongLine
        ||
        getSongRating(
            currentAlbum.id,
            currentSongIndex
        ) !== null;


    if (!cell) {

        return;

    }


    if (!showLive) {

        applyScoreColor(cell, null);

        return;

    }


    cell.textContent =
        currentRating.toFixed(1);

    cell.classList.add("active");

    applyScoreColor(
        cell,
        currentRating
    );

}


function applyScoreColor(element, score) {

    if (!element) {

        return;

    }


    if (
        score === null
        ||
        score === undefined
    ) {

        element.style.color = "";

        element.style.textShadow = "";

        return;

    }


    element.style.color =
        ratingColorValue(score);


    element.style.textShadow =
        ratingGlowValue(score);

}


function scoreColorStyle(score) {

    return (
        `color: ${ratingColorValue(score)}; ` +
        `text-shadow: ${ratingGlowValue(score)};`
    );

}


function updateAlbumScoreChrome() {

    if (!currentAlbum) {

        updateRainbowDot(null);

        return;

    }


    const live =
        getLiveAlbumRating(
            currentAlbum.id
        );


    const score =
        live !== null
        ? live
        : getAlbumRating(
            currentAlbum.id
        );


    const text =
        score !== null
        ? (
            Math.round(score * 10) / 10
        ).toFixed(1)
        : "—";


    const albumScore =
        document.getElementById(
            "currentAlbumScore"
        );


    if (albumScore) {

        albumScore.textContent =
            text;

        applyScoreColor(
            albumScore,
            score
        );

    }


    const heroScore =
        document.getElementById(
            "heroUserScore"
        );


    if (heroScore) {

        heroScore.textContent =
            text;

        applyScoreColor(
            heroScore,
            score
        );

    }


    updateRainbowDot(score);


    const rainbowDot =
        document.getElementById(
            "rainbowDot"
        );


    if (rainbowDot) {

        rainbowDot.style.transition =
            isDraggingSongLine
            ? "none"
            : "";

    }

}


function updateLiveScoreDisplays() {

    updateAlbumScoreChrome();

    updateCurrentSongScoreDisplay();

}

function finishSongRating() {

    if (!currentAlbum) {

        return;

    }


    if (
        !guestRatings[
            currentAlbum.id
        ]
    ) {

        guestRatings[
            currentAlbum.id
        ] = {};

    }


    guestRatings[
        currentAlbum.id
    ][
        currentSongIndex
    ] = currentRating;


    persistAccountRatings(true);

    renderSongs();

    updateAlbumAverage();

}


function updateRatingActionButton() {

    if (!currentAlbum) {

        return;

    }


    const lastSong =
        currentSongIndex >=
        currentAlbum.songs.length - 1;


    const text =
        lastSong
        ? "Done"
        : "Next Song →";


    [
        "ratingActionButton",
        "inlineRatingActionButton"
    ].forEach(id => {

        const button =
            document.getElementById(
                id
            );


        if (button) {

            button.textContent = text;

        }

    });

}


/* =====================================================
   NEXT SONG
===================================================== */

function nextSong() {

    finishSongRating();


    if (
        currentSongIndex <
        currentAlbum.songs.length - 1
    ) {

        currentSongIndex++;


        const savedRating =
            getSongRating(
                currentAlbum.id,
                currentSongIndex
            );


        if (savedRating !== null) {

            currentRating =
                savedRating;

        } else {

            currentRating = 5.0;

        }


        dialWasMoved = false;

        pendingSongScroll = true;


        updateDial();

        updateRatingActionButton();

    } else {

        finishAlbum();

    }

}


/* =====================================================
   ALL SONGS RATED
===================================================== */

function allSongsRated() {

    if (!currentAlbum) {

        return false;

    }


    const ratings =
        guestRatings[
            currentAlbum.id
        ] || {};


    return currentAlbum.songs.every(
        (song, index) =>
            ratings[index] !== undefined
    );

}


/* =====================================================
   FINISH ALBUM
===================================================== */

function finishAlbum() {

    if (!currentAlbum) {

        return;

    }


    const ratings =
        guestRatings[
            currentAlbum.id
        ] || {};


    const values =
        currentAlbum.songs
            .map(
                (song, index) =>
                    ratings[index]
            )
            .filter(
                value =>
                    value !== undefined
            );


    if (values.length === 0) {

        return;

    }


    const average =
        values.reduce(
            (sum, value) =>
                sum + value,
            0
        ) / values.length;


    const final =
        Math.round(
            average * 10
        ) / 10;


    document.getElementById(
        "finalAlbumScore"
    ).textContent =
        final.toFixed(1);


    applyScoreColor(
        document.getElementById(
            "finalAlbumScore"
        ),
        final
    );


    document.getElementById(
        "albumSaveMessage"
    ).textContent = currentUser

        ? "This rating can be saved to your account."

        : "Create an account to permanently save this rating.";


    document
        .getElementById("albumResult")
        .classList.remove("hidden");

}


/* =====================================================
   HIDE RESULT
===================================================== */

function hideAlbumResult() {

    document
        .getElementById("albumResult")
        .classList.add("hidden");

}


/* =====================================================
   GET ALBUM RATING
===================================================== */

function getLiveAlbumRating(albumId) {

    const album =
        albumById.get(albumId);


    if (!album) {

        return null;

    }


    const ratings = {
        ...(
            guestRatings[albumId]
            ||
            {}
        )
    };


    if (
        currentAlbum
        &&
        currentAlbum.id === albumId
        &&
        (
            isDraggingSongLine
            ||
            isDraggingDial
            ||
            dialWasMoved
        )
    ) {

        ratings[currentSongIndex] =
            currentRating;

    }


    const values =
        album.songs
            .map(
                (song, index) =>
                    ratings[index]
            )
            .filter(
                value =>
                    value !== undefined
                    &&
                    value !== null
            );


    if (values.length === 0) {

        return null;

    }


    return (
        values.reduce(
            (a, b) =>
                a + b,
            0
        ) / values.length
    );

}


function getAlbumRating(albumId) {

    const ratings =
        guestRatings[albumId];


    if (!ratings) {

        return null;

    }


    const album =
        albumById.get(albumId);


    if (!album) {

        return null;

    }


    const values =
        album.songs
            .map(
                (song, index) =>
                    ratings[index]
            )
            .filter(
                value =>
                    value !== undefined
            );


    if (values.length === 0) {

        return null;

    }


    const average =
        values.reduce(
            (a, b) =>
                a + b,
            0
        ) / values.length;


    return Math.round(
        average * 10
    ) / 10;

}


/* =====================================================
   UPDATE ALBUM
===================================================== */

function updateAlbumAverage() {

    updateLiveScoreDisplays();

}


/* =====================================================
   SAVE ALBUM
===================================================== */

async function handleSaveAlbum() {

    /*
        Guest:

        Ask them to login/create
        an account.
    */

    if (!currentUser) {

        openAuth();

        return;

    }


    if (!allSongsRated()) {

        return;

    }


    const ratings =
        guestRatings[
            currentAlbum.id
        ] || {};


    persistAccountRatings(true);


    const token =
        localStorage.getItem(
            "ratedToken"
        );


    if (
        !token ||
        token.startsWith("local-")
    ) {

        document.getElementById(
            "albumSaveMessage"
        ).textContent =
            "Saved permanently to your account.";

        renderAlbums();

        return;

    }


    try {

        const response =
            await apiFetch(
                `${API_URL}/ratings`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        Authorization:
                            `Bearer ${token}`
                    },

                    body: JSON.stringify({

                        album_id:
                            currentAlbum.id,

                        album_score:
                            getAlbumRating(
                                currentAlbum.id
                            ),

                        song_ratings:
                            ratings

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Could not save rating."
            );

            return;

        }


        document.getElementById(
            "albumSaveMessage"
        ).textContent =
            "Saved permanently to your account.";


        /*
            Keep guestRatings in memory
            for the current session.
        */

        await loadUserRatings();


        renderAlbums();


    } catch (error) {

        console.error(error);

        alert(
            "Could not connect to the server."
        );

    }

}


/* =====================================================
   LOAD USER RATINGS
===================================================== */

async function loadUserRatings() {

    if (!currentUser) {

        return;

    }


    const token =
        localStorage.getItem(
            "ratedToken"
        );


    if (
        !token ||
        token.startsWith("local-")
    ) {

        const storedRatings =
            localStorage.getItem(
                "ratedRatings_" + currentUser.id
            );

        if (storedRatings) {

            guestRatings =
                JSON.parse(storedRatings);

        } else {

            persistAccountRatings(true);

        }

        renderAlbums();

        return;

    }


    try {

        const response =
            await apiFetch(
                `${API_URL}/ratings`,
                {
                    headers: {
                        Authorization:
                            `Bearer ${token}`
                    }
                }
            );


        if (!response.ok) {

            return;

        }


        const ratings =
            await response.json();


        if (
            ratings &&
            Object.keys(ratings).length
        ) {

            guestRatings = ratings;

        }


        persistAccountRatings(true);

        renderAlbums();


    } catch (error) {

        console.error(error);

    }

}


/* =====================================================
   SAVED ALBUMS
===================================================== */

function renderSaved() {

    const container =
        document.getElementById(
            "savedAlbums"
        );


    const saved =
        albums.filter(
            album =>
                getAlbumRating(
                    album.id
                ) !== null
        );


    container.innerHTML = "";


    if (saved.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                You haven't saved
                any albums yet.

            </div>

        `;

        return;

    }


    container.innerHTML =
        sortAlbumList(saved)
            .map((album, index) =>
                createAlbumCard(album, false, index + 1)
            )
            .join("");

}


/* =====================================================
   PERFECT ALBUMS
===================================================== */

function renderPerfect() {

    const container =
        document.getElementById(
            "perfectAlbums"
        );


    const perfect =
        albums.filter(
            album =>
                getAlbumRating(
                    album.id
                ) === 10
        );


    container.innerHTML = "";


    if (perfect.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                You haven't given
                any album a 10/10 yet.

            </div>

        `;

        return;

    }


    container.innerHTML =
        sortAlbumList(perfect)
            .map((album, index) =>
                createAlbumCard(album, false, index + 1)
            )
            .join("");

}


/* =====================================================
   SEARCH
===================================================== */

function searchAlbums() {

    clearTimeout(searchTimer);

    searchTimer =
        setTimeout(
            applySearch,
            80
        );

}


function applySearch() {

    const input =
        document.getElementById(
            "searchInput"
        );


    const query =
        input.value
            .toLowerCase()
            .trim();


    const filtered =
        albums.filter(
            album =>

                album.title
                    .toLowerCase()
                    .includes(query)

                ||

                album.artist
                    .toLowerCase()
                    .includes(query)

                ||

                album.genre
                    .toLowerCase()
                    .includes(query)
        );


    const artistsPage =
        document.getElementById(
            "artistsPage"
        );


    const artistPage =
        document.getElementById(
            "artistPage"
        );


    const searchingArtists =
        !artistsPage.classList.contains("hidden")
        ||
        !artistPage.classList.contains("hidden");


    if (searchingArtists) {

        const artistMatches =
            getArtistDirectory().filter(
                artist =>
                    artist.name
                        .toLowerCase()
                        .includes(query)
            );


        hideAllPages();

        setActiveNav("navArtists");

        document
            .getElementById("artistsPage")
            .classList.remove("hidden");

        renderArtists(artistMatches);

        return;

    }


    hideAllPages();

    setActiveNav("navHome");

    document
        .getElementById("homePage")
        .classList.remove("hidden");

    renderAlbums(filtered);

}


/* =====================================================
   AUTH
===================================================== */

function openAuth() {

    document
        .getElementById("authModal")
        .classList.remove("hidden");


    if (currentUser) {

        showAccount();

    } else {

        showLogin();

    }

}


function closeAuth() {

    document
        .getElementById("authModal")
        .classList.add("hidden");

}


function showLogin() {

    document
        .getElementById("loginForm")
        .classList.remove("hidden");


    document
        .getElementById("registerForm")
        .classList.add("hidden");


    document
        .getElementById("authTitle")
        .textContent =
        "Welcome back";


    document
        .getElementById("authSubtitle")
        .textContent =
        "Login to save your ratings.";


    clearAuthMessage();

}


function showRegister() {

    document
        .getElementById("loginForm")
        .classList.add("hidden");


    document
        .getElementById("registerForm")
        .classList.remove("hidden");


    document
        .getElementById("authTitle")
        .textContent =
        "Create your account";


    document
        .getElementById("authSubtitle")
        .textContent =
        "Create an account to permanently save your ratings.";


    clearAuthMessage();

}


function apiErrorMessage(data, fallback) {

    const detail = data && data.detail;

    if (typeof detail === "string") {

        return detail;

    }

    if (Array.isArray(detail) && detail.length) {

        return detail
            .map(item => item.msg || item)
            .join(" ");

    }

    return fallback;

}


function saveSession(data, tokenOverride) {

    const token =
        tokenOverride ||
        data.token ||
        data.access_token;

    if (!token) {

        throw new Error(
            "Server did not return a login token."
        );

    }

    localStorage.setItem(
        "ratedToken",
        token
    );

    currentUser = data.user;

    localStorage.setItem(
        "ratedUser",
        JSON.stringify(currentUser)
    );

    updateProfileButton();

}


async function hashSecret(value) {

    const buffer =
        await crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(value)
        );

    return Array.from(
        new Uint8Array(buffer)
    ).map(
        byte => byte.toString(16).padStart(2, "0")
    ).join("");

}


function getLocalUsers() {

    try {

        return JSON.parse(
            localStorage.getItem(
                "ratedLocalUsers"
            ) || "[]"
        );

    } catch (error) {

        return [];

    }

}


function restoreLocalSession() {

    const token =
        localStorage.getItem("ratedToken");

    const savedUser =
        localStorage.getItem("ratedUser");


    if (!token || !savedUser) {

        return false;

    }


    try {

        currentUser = JSON.parse(savedUser);

    } catch (error) {

        return false;

    }


    const storedRatings =
        localStorage.getItem(
            "ratedRatings_" + currentUser.id
        );


    if (storedRatings) {

        try {

            guestRatings =
                JSON.parse(storedRatings);

        } catch (error) {

            guestRatings = guestRatings || {};

        }

    } else {

        persistAccountRatings(true);

    }


    updateProfileButton();

    renderAlbums();

    return true;

}


async function createLocalAccount(username, email, password, profilePicture) {

    const users = getLocalUsers();

    email = email.toLowerCase();


    if (
        users.some(
            user =>
                user.username.toLowerCase() ===
                username.toLowerCase()
        )
    ) {

        throw new Error(
            "Username is already taken."
        );

    }


    if (
        users.some(
            user => user.email === email
        )
    ) {

        throw new Error(
            "An account with this email already exists."
        );

    }


    const salt =
        crypto.randomUUID();

    const user = {
        id: Date.now(),
        username,
        email,
        salt,
        password_hash:
            await hashSecret(salt + password),
        profile_picture: profilePicture
    };


    users.push(user);

    localStorage.setItem(
        "ratedLocalUsers",
        JSON.stringify(users)
    );


    saveSession(
        {
            user: {
                id: user.id,
                username: user.username,
                email: user.email,
                profile_picture:
                    user.profile_picture
            }
        },
        "local-" + user.id
    );


    persistAccountRatings(true);

}


async function loginLocalAccount(email, password) {

    const users = getLocalUsers();

    email = email.toLowerCase();

    const user =
        users.find(
            item => item.email === email
        );


    if (!user) {

        throw new Error(
            "Incorrect email or password."
        );

    }


    const passwordHash =
        await hashSecret(
            user.salt + password
        );


    if (passwordHash !== user.password_hash) {

        throw new Error(
            "Incorrect email or password."
        );

    }


    saveSession(
        {
            user: {
                id: user.id,
                username: user.username,
                email: user.email,
                profile_picture:
                    user.profile_picture
            }
        },
        "local-" + user.id
    );


    const storedRatings =
        localStorage.getItem(
            "ratedRatings_" + user.id
        );


    if (storedRatings) {

        guestRatings =
            JSON.parse(storedRatings);

    } else {

        persistAccountRatings(true);

    }

}


function clearAuthMessage() {

    document
        .getElementById("authMessage")
        .textContent = "";

}


/* =====================================================
   REGISTER
===================================================== */

async function register(event) {

    event.preventDefault();


    const username =
        document.getElementById(
            "registerUsername"
        ).value.trim();


    const email =
        document.getElementById(
            "registerEmail"
        ).value.trim();


    const password =
        document.getElementById(
            "registerPassword"
        ).value;


    const pfpInput =
        document.getElementById(
            "registerPfp"
        );


    const message =
        document.getElementById(
            "authMessage"
        );


    message.textContent =
        "Creating account...";


    let profilePicture = null;


    /*
        For this starter version
        we convert the profile picture
        into a base64 string.

        Later this should be moved
        to real file storage.
    */

    if (
        pfpInput.files.length > 0
    ) {

        if (pfpInput.files[0].size > 2 * 1024 * 1024) {

            message.textContent =
                "Profile picture must be under 2 MB.";

            return;

        }

        profilePicture =
            await fileToBase64(
                pfpInput.files[0]
            );

    }


    try {

        const response =
            await apiFetch(
                `${API_URL}/register`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        username,

                        email,

                        password,

                        profile_picture:
                            profilePicture

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            message.textContent =
                apiErrorMessage(
                    data,
                    "Could not create account."
                );

            return;

        }


        saveSession(data);

        persistAccountRatings(true);

        await loadUserRatings();


        /*
            Guest ratings are now
            still in memory.

            Ask whether they want
            to save the current album.
        */

        message.textContent =
            "Account created.";


        setTimeout(
            () => {

                closeAuth();

                if (
                    currentAlbum &&
                    allSongsRated()
                ) {

                    handleSaveAlbum();

                }

            },
            500
        );


    } catch (error) {

        console.error(error);

        try {

            await createLocalAccount(
                username,
                email,
                password,
                profilePicture
            );

            message.textContent =
                "Account created.";

            setTimeout(
                () => {

                    closeAuth();

                    if (
                        currentAlbum &&
                        allSongsRated()
                    ) {

                        handleSaveAlbum();

                    }

                },
                500
            );

        } catch (localError) {

            message.textContent =
                localError.message ||
                "Could not create account.";

        }

    }

}


async function login(event) {

    event.preventDefault();


    const email =
        document.getElementById(
            "loginEmail"
        ).value.trim();


    const password =
        document.getElementById(
            "loginPassword"
        ).value;


    const message =
        document.getElementById(
            "authMessage"
        );


    message.textContent =
        "Logging in...";


    try {

        const response =
            await apiFetch(
                `${API_URL}/login`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        email,

                        password

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            message.textContent =
                apiErrorMessage(
                    data,
                    "Login failed."
                );

            return;

        }


        saveSession(data);

        persistAccountRatings(true);

        await loadUserRatings();


        message.textContent =
            "Logged in.";


        setTimeout(
            () => {

                closeAuth();

            },
            500
        );


    } catch (error) {

        console.error(error);

        try {

            await loginLocalAccount(
                email,
                password
            );

            renderAlbums();

            message.textContent =
                "Logged in.";

            setTimeout(
                () => {

                    closeAuth();

                },
                500
            );

        } catch (localError) {

            message.textContent =
                localError.message ||
                "Could not connect to the server.";

        }

    }

}


/* =====================================================
   ACCOUNT VIEW
===================================================== */

function showAccount() {

    document
        .getElementById("loginForm")
        .classList.add("hidden");


    document
        .getElementById("registerForm")
        .classList.add("hidden");


    document
        .getElementById("authTitle")
        .textContent =
        currentUser.username;


    document
        .getElementById("authSubtitle")
        .textContent =
        currentUser.email;


    document
        .getElementById("authMessage")
        .innerHTML = `

            <button
                onclick="logout()"
                style="
                    margin-top:15px;
                    padding:10px 20px;
                    border:1px solid #292929;
                    background:#151515;
                    color:white;
                    border-radius:5px;
                    cursor:pointer;
                "
            >
                Logout
            </button>

        `;

}


/* =====================================================
   LOGOUT
===================================================== */

function logout() {

    localStorage.removeItem(
        "ratedToken"
    );

    localStorage.removeItem(
        "ratedUser"
    );


    currentUser = null;


    /*
        Remove ratings from memory
        after logout so another user
        cannot see them.
    */

    guestRatings = {};


    updateProfileButton();


    closeAuth();

    showHome();

    renderAlbums();

}


/* =====================================================
   FILE TO BASE64
===================================================== */

function fileToBase64(file) {

    return new Promise(
        (resolve, reject) => {

            const reader =
                new FileReader();


            reader.onload = () =>
                resolve(
                    reader.result
                );


            reader.onerror =
                reject;


            reader.readAsDataURL(file);

        }
    );

}