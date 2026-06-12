import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents3

PlasmoidItem {
    id: root

    clip: true

    property var summary: ({"text": "--", "tooltip": "CodexBar is loading…", "class": "stale", "percentage": 0, "providers": []})
    property var cost: ({"cost": [], "updatedAt": ""})
    property string errorText: ""
    property string errorDetails: ""
    property bool busy: false
    property bool showSettings: false
    property bool settingsDirty: false
    property var _pendingChanges: ({})
    property var settings: ({"providers": [], "pinnableProviders": [], "pinnedProvider": "", "refreshIntervalSeconds": 30, "allAccounts": true, "statusPages": false, "noCredits": false, "showBarText": true, "showAccountEmail": true, "providerOrder": "[]", "plasmoidVersion": "", "cliVersion": ""})
    property string settingsQuery: ""
    property string helperPath: localFilePath(Qt.resolvedUrl("../code/codexbar_kde.py"))
    property url codexbarIcon: Qt.resolvedUrl("../images/codexbar.png")

    // Closing the popup resets back to the usage page and drops any
    // uncommitted settings, so reopening never lands on Settings.
    onExpandedChanged: {
        if (!expanded) {
            showSettings = false
            settingsDirty = false
            _pendingChanges = {}
        }
    }

    ListModel {
        id: providerOrderModel
    }

    Plasmoid.icon: "codexbar"
    toolTipMainText: "CodexBar"
    toolTipSubText: summary.tooltip || errorText || "No provider data yet"
    preferredRepresentation: compactRepresentation

    function localFilePath(url) {
        var text = String(url)
        if (text.indexOf("file://") === 0) {
            return decodeURIComponent(text.substring(7))
        }
        return text
    }

    function shellQuote(path) {
        return "'" + String(path).replace(/'/g, "'\\''") + "'"
    }

    function runHelper(command) {
        busy = true
        errorText = ""
        errorDetails = ""
        executor.connectSource("python3 " + shellQuote(helperPath) + " " + command)
    }

    function refresh() {
        runHelper("summary")
    }

    function loadCache() {
        runHelper("cache")
    }

    function loadSettings() {
        runHelper("settings")
    }

    function setProviderEnabled(providerId, enabled) {
        settingsDirty = true
        runHelper("set-provider --provider " + providerId + " --enabled " + (enabled ? "true" : "false"))
    }

    // Keys that change which data is pulled over the network — these need a
    // full (slow) summary refetch on apply.
    readonly property var _networkKeys: ["allAccounts", "statusPages", "noCredits"]
    // Keys that only change how already-cached data is rendered by the helper.
    // The popup card list (root.summary.providers) is ordered, and the bar
    // text is picked, in Python (summarize/_sort_by_order/bar_text), so these
    // need a fast, local cache recompute (no network) to re-render.
    readonly property var _recomputeKeys: ["barProvider", "providerOrder"]
    // Everything else (showBarText, showAccountEmail, …) is pure QML display,
    // already live via the optimistic write below.

    function saveStateKey(key, value) {
        // Changes stay pending until the user presses OK/Apply — they must not
        // affect the live bar before then.
        _pendingChanges[key] = value
        settingsDirty = true
    }

    function flushPendingChanges() {
        var keys = Object.keys(_pendingChanges)
        if (keys.length === 0) return
        var pairs = []
        for (var i = 0; i < keys.length; i++) {
            var k = keys[i]
            pairs.push('["' + k.replace(/\\/g,'\\\\').replace(/"/g,'\\"') + '","' + String(_pendingChanges[k]).replace(/\\/g,'\\\\').replace(/"/g,'\\"') + '"]')
        }
        runHelper("batch-set-state --json '[" + pairs.join(",") + "]'")
        _pendingChanges = {}
    }

    function fetchCost() {
        runHelper("cost")
    }

    function cacheClear() {
        runHelper("cache-clear")
    }

    function toggleSettings() {
        showSettings = !showSettings
        settingsDirty = false
        _pendingChanges = {}
        if (showSettings) {
            loadSettings()
        }
    }

    function settingsOk() {
        settingsApply()
        showSettings = false
    }

    function settingsApply() {
        // Snapshot the pending keys before flush clears the map.
        var keys = Object.keys(_pendingChanges)
        var needsRefetch = keys.some(function(k) {
            return root._networkKeys.indexOf(k) !== -1
        })
        var needsRecompute = keys.some(function(k) {
            return root._recomputeKeys.indexOf(k) !== -1
        })

        // Apply the pending values to root.settings locally so display-only
        // bindings (bar text, email visibility, …) update the instant Apply is
        // pressed — no CLI round-trip. Reassign a fresh object so bindings
        // re-evaluate; coerce "true"/"false" to bool to match the helper's
        // settings payload types (settings_payload in codexbar_kde.py).
        var s = Object.assign({}, root.settings)
        for (var i = 0; i < keys.length; i++) {
            var k = keys[i]
            var v = _pendingChanges[k]
            if (v === "true") s[k] = true
            else if (v === "false") s[k] = false
            else s[k] = v
        }
        root.settings = s

        flushPendingChanges()
        settingsDirty = false

        // Only hit the network when a fetched-data key changed; otherwise a
        // fast local cache recompute covers bar-text/ordering changes, and
        // pure-display changes need nothing further.
        if (needsRefetch) refresh()
        else if (needsRecompute) loadCache()
    }

    function settingsCancel() {
        // Discard pending changes; root.settings was never touched, so the
        // live bar is already correct.
        _pendingChanges = {}
        settingsDirty = false
        showSettings = false
    }

    function filteredSettingsProviders() {
        var providers = settings.providers || []
        var query = settingsQuery.trim().toLowerCase()
        if (!query) {
            return providers
        }

        return providers.filter(function(provider) {
            var haystack = [
                provider.id || "",
                provider.displayName || "",
                provider.accountText || "",
                provider.connectHint || ""
            ].join(" ").toLowerCase()
            return haystack.indexOf(query) !== -1
        })
    }

    function refreshProviderOrderModel() {
        providerOrderModel.clear()

        var orderArray = []
        try {
            var parsed = JSON.parse(settings.providerOrder || "[]")
            if (Array.isArray(parsed)) orderArray = parsed
        } catch (e) {}

        var allProviders = (settings.providers || []).filter(function(p) { return p.enabled !== false })
        var seen = {}
        var ordered = []

        for (var i = 0; i < orderArray.length; i++) {
            var oid = orderArray[i]
            for (var j = 0; j < allProviders.length; j++) {
                if (allProviders[j].id === oid) {
                    ordered.push({ id: oid, displayName: allProviders[j].displayName || oid })
                    seen[oid] = true
                    break
                }
            }
        }

        for (var k = 0; k < allProviders.length; k++) {
            var pid = allProviders[k].id || ""
            if (pid && !seen[pid]) {
                ordered.push({ id: pid, displayName: allProviders[k].displayName || pid })
            }
        }

        for (var m = 0; m < ordered.length; m++) {
            providerOrderModel.append({ providerId: ordered[m].id, displayName: ordered[m].displayName })
        }
    }

    function saveProviderOrder() {
        var ids = []
        for (var i = 0; i < providerOrderModel.count; i++) {
            ids.push(providerOrderModel.get(i).providerId)
        }
        saveStateKey("providerOrder", JSON.stringify(ids))
    }

    function windowList(entry) {
        if (!entry || !entry.usage) {
            return []
        }
        var result = []
        var keys = ["primary", "secondary", "tertiary"]
        var labels = {"primary": "Session", "secondary": "Weekly", "tertiary": "Monthly"}
        for (var i = 0; i < keys.length; i++) {
            var key = keys[i]
            var win = entry.usage[key]
            if (win && win.usedPercent !== undefined && win.usedPercent !== null) {
                result.push({
                    "key": key,
                    "label": labels[key],
                    "percent": Number(win.usedPercent),
                    "reset": win.resetDescription || ""
                })
            }
        }
        return result
    }

    function levelColor(percent) {
        if (percent >= 90) {
            return "#ff453a"
        }
        if (percent >= 70) {
            return "#ff9f0a"
        }
        return "#0a84ff"
    }

    function compactLabelPct() {
        var pinned = root.summary.barProvider || ""
        if (pinned) {
            var providers = root.summary.providers || []
            for (var i = 0; i < providers.length; i++) {
                if (providers[i].provider === pinned) {
                    return providers[i].maxPercent || 0
                }
            }
        }
        return root.summary.percentage || 0
    }

    function providerCostEntry(usageEntry) {
        if (!usageEntry || !usageEntry.provider) return null
        var items = root.cost.cost || []
        for (var i = 0; i < items.length; i++) {
            if (items[i].provider === usageEntry.provider) {
                var cost = items[i].last30DaysCostUSD || items[i].sessionCostUSD
                if (cost !== undefined && cost !== null) {
                    return Number(cost).toFixed(2) + " (30d)"
                }
                cost = items[i].sessionCostUSD
                if (cost !== undefined && cost !== null) {
                    return Number(cost).toFixed(2) + " (session)"
                }
                return null
            }
        }
        return null
    }

    Component.onCompleted: {
        loadCache()
        refresh()
    }

    Timer {
        interval: root.settings.refreshIntervalSeconds ? root.settings.refreshIntervalSeconds * 1000 : 30000
        repeat: true
        running: true
        triggeredOnStart: false
        onTriggered: root.refresh()
    }

    Plasma5Support.DataSource {
        id: executor
        engine: "executable"
        connectedSources: []

        onNewData: function(sourceName, data) {
            executor.disconnectSource(sourceName)
            root.busy = false

            var isSetState = sourceName.indexOf(" set-state ") !== -1 || sourceName.indexOf(" batch-set-state ") !== -1

            if (isSetState) {
                if (data["exit code"] !== 0) {
                    root.errorText = "An error occurred."
                    root.errorDetails = data.stderr || "state save failed"
                }
                return
            }

            if (data["exit code"] !== 0) {
                root.errorText = "An error occurred."
                root.errorDetails = data.stderr || data.stdout || "codexbar helper failed"
                return
            }

            try {
                var payload = JSON.parse(data.stdout)
                var isSettings = sourceName.indexOf(" settings") !== -1
                var isSetProvider = sourceName.indexOf(" set-provider ") !== -1
                var isCost = sourceName.indexOf(" cost") !== -1
                var isCacheClear = sourceName.indexOf(" cache-clear") !== -1

                if (isCost) {
                    root.cost = payload
                } else if (isCacheClear) {
                    root.refresh()
                } else if (isSettings || isSetProvider) {
                    root.settings = payload
                    root.refreshProviderOrderModel()
                    if (isSetProvider) root.refresh()
                } else {
                    root.summary = payload
                }
                root.errorText = ""
                root.errorDetails = ""
            } catch (e) {
                root.errorText = "Invalid JSON from codexbar helper"
                root.errorDetails = String(e) + "\n\nOutput:\n" + (data.stdout || "")
            }
        }
    }

    compactRepresentation: Item {
        implicitWidth: compactRow.implicitWidth + Kirigami.Units.smallSpacing * 2
        implicitHeight: Math.max(Kirigami.Units.iconSizes.smallMedium, compactLabel.implicitHeight) + Kirigami.Units.smallSpacing * 2

        // Make the panel slot track the content width at runtime. Without
        // these, Plasma reads implicitWidth once and won't shrink/grow when
        // the bar text is toggled, clipping the icon and cutting the text.
        Layout.minimumWidth: implicitWidth
        Layout.maximumWidth: implicitWidth

        clip: true

        Rectangle {
            anchors.fill: parent
            radius: Kirigami.Units.smallSpacing
            color: compactMouse.containsMouse ? Kirigami.Theme.hoverColor : "transparent"
            opacity: compactMouse.containsMouse ? 0.25 : 1
        }

        RowLayout {
            id: compactRow
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing

            Image {
                source: root.codexbarIcon
                Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            PlasmaComponents3.Label {
                id: compactLabel
                visible: root.settings.showBarText !== false
                text: root.summary.text || "--"
                wrapMode: Text.NoWrap
                elide: Text.ElideRight
                color: {
                    var pct = compactLabelPct()
                    return pct < 70 ? Kirigami.Theme.textColor : root.levelColor(pct)
                }
                font.bold: compactLabelPct() >= 90
            }
        }

        MouseArea {
            id: compactMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.expanded = !root.expanded
        }
    }

    fullRepresentation: FullPopup { }
}
