import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

QQC2.ScrollView {
    id: settingsScroll
    Layout.fillWidth: true
    Layout.fillHeight: true
    clip: true
    contentWidth: availableWidth
    QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff

    ColumnLayout {
        width: settingsScroll.availableWidth
        spacing: Kirigami.Units.smallSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            ColumnLayout {
                spacing: 0

                PlasmaComponents3.Label {
                    text: "Refresh every"
                    opacity: 0.8
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.SpinBox {
                    from: 10
                    to: 600
                    stepSize: 10
                    value: root.settings.refreshIntervalSeconds || 30
                    editable: true
                    onValueChanged: {
                        var v = value
                        if (v !== root.settings.refreshIntervalSeconds) {
                            root.settings.refreshIntervalSeconds = v
                            root.saveStateKey("refreshIntervalSeconds", String(v))
                        }
                    }
                }
            }

            PlasmaComponents3.Label {
                text: "seconds"
                Layout.alignment: Qt.AlignBottom
                opacity: 0.7
                bottomPadding: Kirigami.Units.smallSpacing
            }

            Item { Layout.fillWidth: true }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            ColumnLayout {
                spacing: 0

                PlasmaComponents3.Label {
                    text: "All accounts"
                    opacity: 0.8
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.Switch {
                    id: allAccountsSwitch
                    checked: root.settings.allAccounts !== false
                    onToggled: root.saveStateKey("allAccounts", checked ? "true" : "false")

                    QQC2.ToolTip.visible: allAccountsSwitch.hovered
                    QQC2.ToolTip.text: "When on: fetches every account for each provider (--all-accounts).\nWhen off: uses only the default CLI account, or the specific account set per provider below."
                    QQC2.ToolTip.delay: 500
                }
            }

            ColumnLayout {
                spacing: 0

                PlasmaComponents3.Label {
                    text: "Status pages"
                    opacity: 0.8
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.Switch {
                    id: statusPagesSwitch
                    checked: root.settings.statusPages === true
                    onToggled: root.saveStateKey("statusPages", checked ? "true" : "false")

                    QQC2.ToolTip.visible: statusPagesSwitch.hovered
                    QQC2.ToolTip.text: "When on: fetches provider status page info (--status).\nMay cause errors with some providers. Leave off if you see token errors."
                    QQC2.ToolTip.delay: 500
                }
            }

            ColumnLayout {
                spacing: 0

                PlasmaComponents3.Label {
                    text: "Hide credits"
                    opacity: 0.8
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.Switch {
                    id: noCreditsSwitch
                    checked: root.settings.noCredits === true
                    onToggled: root.saveStateKey("noCredits", checked ? "true" : "false")

                    QQC2.ToolTip.visible: noCreditsSwitch.hovered
                    QQC2.ToolTip.text: "When on: passes --no-credits to hide Codex credit info from output."
                    QQC2.ToolTip.delay: 500
                }
            }

            ColumnLayout {
                spacing: 0

                PlasmaComponents3.Label {
                    text: "Show bar text"
                    opacity: 0.8
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.Switch {
                    id: showBarTextSwitch
                    checked: root.settings.showBarText !== false
                    onToggled: root.saveStateKey("showBarText", checked ? "true" : "false")

                    QQC2.ToolTip.visible: showBarTextSwitch.hovered
                    QQC2.ToolTip.text: "Show usage percentage next to the icon in the panel bar."
                    QQC2.ToolTip.delay: 500
                }
            }

            ColumnLayout {
                spacing: 0

                PlasmaComponents3.Label {
                    text: "Show account email"
                    opacity: 0.8
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.Switch {
                    id: showAccountEmailSwitch
                    checked: root.settings.showAccountEmail !== false
                    onToggled: root.saveStateKey("showAccountEmail", checked ? "true" : "false")

                    QQC2.ToolTip.visible: showAccountEmailSwitch.hovered
                    QQC2.ToolTip.text: "Show the account email/identity below each provider in the usage view."
                    QQC2.ToolTip.delay: 500
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Kirigami.Theme.disabledTextColor
            opacity: 0.18
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                PlasmaComponents3.Label {
                    text: "Pin to panel bar"
                    opacity: 0.8
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.ComboBox {
                    Layout.fillWidth: true
                    model: ["— none —"].concat((root.settings.pinnableProviders || []).map(function(p) { return p.displayName || p.id }))
                    currentIndex: {
                        var pinned = root.settings.pinnedProvider || ""
                        if (!pinned) return 0
                        var list = root.settings.pinnableProviders || []
                        for (var i = 0; i < list.length; i++) {
                            if (list[i].id === pinned) return i + 1
                        }
                        return 0
                    }
                    onActivated: {
                        if (index === 0) {
                            root.saveStateKey("barProvider", "")
                        } else {
                            var list = root.settings.pinnableProviders || []
                            var picked = list[index - 1]
                            root.saveStateKey("barProvider", picked.id || "")
                        }
                        root.refresh()
                    }
                }
            }

            ColumnLayout {
                Layout.alignment: Qt.AlignBottom

                QQC2.ToolButton {
                    text: "Clear Cache"
                    icon.name: "edit-clear-history"
                    display: QQC2.AbstractButton.TextBesideIcon
                    onClicked: root.cacheClear()

                    QQC2.ToolTip.visible: hovered
                    QQC2.ToolTip.text: "Clears CodexBar browser cookies and cost caches,\nplus the widget's last-good data. Refresh after clearing."
                    QQC2.ToolTip.delay: 500
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Kirigami.Theme.disabledTextColor
            opacity: 0.18
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents3.Label {
                text: "Provider order"
                font.bold: true
                opacity: 0.8
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            PlasmaComponents3.Label {
                text: "Drag to reorder. Changes take effect on next refresh."
                wrapMode: Text.WordWrap
                opacity: 0.65
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            ListView {
                id: providerOrderList
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(providerOrderList.contentHeight > 0 ? providerOrderList.contentHeight : (providerOrderModel.count * Kirigami.Units.gridUnit * 2), Kirigami.Units.gridUnit * 14)
                clip: true
                interactive: providerOrderModel.count > 0
                model: providerOrderModel

                moveDisplaced: Transition {
                    YAnimator {
                        duration: Kirigami.Units.longDuration
                        easing.type: Easing.InOutQuad
                    }
                }

                delegate: QQC2.ItemDelegate {
                    id: dragItem
                    width: providerOrderList.width

                    contentItem: RowLayout {
                        spacing: 0

                        Kirigami.ListItemDragHandle {
                            listItem: dragItem
                            listView: providerOrderList
                            onMoveRequested: function(oldIndex, newIndex) {
                                providerOrderModel.move(oldIndex, newIndex, 1)
                            }
                            onDropped: root.saveProviderOrder()
                        }

                        PlasmaComponents3.Label {
                            Layout.fillWidth: true
                            text: model.displayName || model.providerId || ""
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            PlasmaComponents3.Label {
                visible: providerOrderModel.count === 0
                Layout.fillWidth: true
                text: "No providers available. Ensure at least one provider is enabled."
                wrapMode: Text.WordWrap
                opacity: 0.65
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Kirigami.Theme.disabledTextColor
            opacity: 0.18
        }

        QQC2.TextField {
            Layout.fillWidth: true
            text: root.settingsQuery
            placeholderText: "Search providers"
            selectByMouse: true
            leftPadding: Kirigami.Units.gridUnit * 1.6
            onTextChanged: root.settingsQuery = text

            Kirigami.Icon {
                anchors.left: parent.left
                anchors.leftMargin: Kirigami.Units.smallSpacing
                anchors.verticalCenter: parent.verticalCenter
                width: Kirigami.Units.iconSizes.small
                height: Kirigami.Units.iconSizes.small
                source: "search"
                opacity: 0.65
            }
        }

        PlasmaComponents3.Label {
            Layout.fillWidth: true
            text: "Enable or disable providers here. Use the connection instructions below each provider to switch accounts."
            wrapMode: Text.WordWrap
            opacity: 0.75
        }

        PlasmaComponents3.Label {
            visible: root.filteredSettingsProviders().length === 0
            Layout.fillWidth: true
            text: "No providers match \u201c" + root.settingsQuery + "\u201d."
            wrapMode: Text.WordWrap
            opacity: 0.7
        }

        Repeater {
            model: root.filteredSettingsProviders()

            delegate: ColumnLayout {
                id: settingsRow
                required property var modelData
                required property int index
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        PlasmaComponents3.Label {
                            Layout.fillWidth: true
                            text: settingsRow.modelData.displayName || settingsRow.modelData.id
                            font.bold: true
                            elide: Text.ElideRight
                        }

                        PlasmaComponents3.Label {
                            visible: (settingsRow.modelData.accountText || "").length > 0
                            Layout.fillWidth: true
                            text: settingsRow.modelData.accountText || ""
                            opacity: 0.7
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            elide: Text.ElideRight
                        }
                    }

                    QQC2.Switch {
                        checked: settingsRow.modelData.enabled === true
                        enabled: settingsRow.modelData.linuxSupported !== false || checked
                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                        onToggled: root.setProviderEnabled(settingsRow.modelData.id, checked)
                    }
                }

                PlasmaComponents3.Label {
                    visible: settingsRow.modelData.linuxSupported === false
                    Layout.fillWidth: true
                    text: settingsRow.modelData.linuxUnsupportedMessage || "This provider is not supported on Linux by the current CodexBar CLI."
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.neutralTextColor
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                RowLayout {
                    visible: settingsRow.modelData.enabled === true && settingsRow.modelData.linuxSupported !== false
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        PlasmaComponents3.Label {
                            text: "Account"
                            opacity: 0.8
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }

                        QQC2.TextField {
                            Layout.fillWidth: true
                            text: settingsRow.modelData.userAccount || ""
                            placeholderText: "All accounts"
                            selectByMouse: true
                            onEditingFinished: {
                                root.saveStateKey("account:" + settingsRow.modelData.id, text.trim())
                                settingsRow.modelData.userAccount = text.trim()
                            }

                            QQC2.ToolTip.visible: hovered
                            QQC2.ToolTip.text: "Leave empty to use --all-accounts (or the CLI default if All Accounts is off).\nType an account label/email to fetch only that account via --account."
                            QQC2.ToolTip.delay: 500
                        }
                    }

                    ColumnLayout {
                        spacing: 0

                        PlasmaComponents3.Label {
                            text: "Source"
                            opacity: 0.8
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }

                        QQC2.ComboBox {
                            id: sourceCombo
                            model: settingsRow.modelData.availableSources || ["auto"]
                            currentIndex: {
                                var src = settingsRow.modelData.userSource || "auto"
                                var list = settingsRow.modelData.availableSources || ["auto"]
                                var idx = list.indexOf(src)
                                return idx >= 0 ? idx : 0
                            }
                            onActivated: {
                                var list = settingsRow.modelData.availableSources || ["auto"]
                                var picked = list[index]
                                root.saveStateKey("source:" + settingsRow.modelData.id, picked)
                                settingsRow.modelData.userSource = picked
                            }

                            QQC2.ToolTip.visible: sourceCombo.hovered
                            QQC2.ToolTip.text: "Override the data source. \"auto\" picks the best available source.\n\"oauth\" uses the provider's OAuth token, \"cli\" reads local CLI data, \"api\" uses an API key."
                            QQC2.ToolTip.delay: 500
                        }
                    }
                }

                PlasmaComponents3.Label {
                    Layout.fillWidth: true
                    text: settingsRow.modelData.connectHint || "Configure credentials in CodexBar, then refresh."
                    wrapMode: Text.WordWrap
                    opacity: 0.75
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                Repeater {
                    model: settingsRow.modelData.accounts || []
                    delegate: PlasmaComponents3.Label {
                        required property var modelData
                        Layout.fillWidth: true
                        text: (modelData.active === "true" ? "• Active account: " : "• Account: ") + modelData.label
                        wrapMode: Text.WordWrap
                        opacity: 0.7
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                }

                Rectangle {
                    visible: settingsRow.index < root.filteredSettingsProviders().length - 1
                    Layout.fillWidth: true
                    height: 1
                    color: Kirigami.Theme.disabledTextColor
                    opacity: 0.18
                }
            }
        }
    }
}
