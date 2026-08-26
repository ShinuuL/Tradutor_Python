//=============================================================================
// MessageWindowHidden.js
// ----------------------------------------------------------------------------
// (C)2015 Triacontane
// This software is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
// 2.7.1 2023/01/17 Fixed an issue where a message would be sent when returning with a left-click during decision operation.
// 2.7.0 2022/09/12 Added a setting to be able to redisplay the window by decision operation when deleting the window (by unaunagi)
// 2.6.1 2020/05/21 Corrected the description that could cause errors depending on the state of the trigger switch and the state of the联动无效开关.
// 2.6.0 2020/05/20 Add a switch to disable picture linkage
// 2.5.1 2020/05/19 Fix the issue where transparency of linked display pictures could not be restored due to the specifications change in version 2.3.0
// 2.5.0 2020/05/17 Add a function to switch the visibility of the window on and off in response to a specified switch
// 2.4.0 2020/05/08 Add a setting to be able to hide the window even while options are being displayed
// 2.3.0 2019/10/22 Change the specification so that when the window is restored to its displayed state, the linked picture will be restored to its originally displayed transparency
// 2.2.0 2019/06/09 Add a function to automatically switch the visibility of the specified picture on and off in response to the linkage with the message window
// 2.1.0 2018/10/10 Add a function to disable the plugin during battle
// 2.0.0 2018/03/31 Add a function to specify multiple triggers for deletion. Review the method of specifying parameters.
// 1.4.0 2018/03/10 Add a function to disable window deletion while a specified switch is ON
// 1.3.2 2017/08/02 Resolve conflict with ponidog_BackLog_utf8.js
// 1.3.1 2017/07/03 The issue where the name display window of the old YEP_MessageCore.js cannot be redisplayed has been fixed (by DarkPlasma)
// 1.3.0 2017/03/16 Added the functionality to specify multiple pictures that can be automatically hidden in conjunction with the message window
// 1.2.1 2017/02/07 Removed device-dependent descriptions
// 1.2.0 2016/01/02 Added the functionality for the picture's display to automatically switch on and off in conjunction with the message window
// 1.1.0 2016/08/25 Changed the specification so that the window cannot be hidden while options are being displayed
// 1.0.4 2016/07/22 Added the functionality to work in conjunction with the name display window of YEP_MessageCore.js
// 1.0.3 2016/01/24 Fixed the issue where the message window could be hidden even when it was not displayed
// 1.0.2 2016/01/02 Countermeasure
// 1.0.1 2015/12/31 Added comments and English support (no changes to specifications)
// 1.0.0 2015/12/30 First edition
// ----------------------------------------------------------------------------
// [Blog]   : https://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:
 * @plugindesc Erase message window
 * @author triacontane
 *
 * @param triggerButton
 * @desc Trigger buttons
 * (light_click or shift or control)
 * @default ["light_click"]
 * @type combo[]
 * @option light_click
 * @option shift
 * @option control
 * @option tab
 * @option pageup
 * @option pagedown
 * @option debug
 *
 * @param triggerSwitch
 * @desc The window will be erased in conjunction with the specified switch.
 * @default 0
 * @type switch
 *
 * @param linkPictureNumbers
 * @desc Picture number of window show/hide
 * @default []
 * @type number[]
 *
 * @param linkShowPictureNumbers
 * @desc Picture number of window show/hide
 * @default []
 * @type number[]
 *
 * @param disableLinkSwitchId
 * @desc 指定した番号のスイッチがONのとき、ピクチャの連動が無効になります。
 * @default 0
 * @type switch
 *
 * @param disableSwitchId
 * @desc 指定した番号のスイッチがONのとき、プラグインの機能が無効になります。
 * @default 0
 * @type switch
 *
 * @param disableInBattle
 * @desc trueのとき、戦闘中にプラグインの機能を無効にします。
 * @default false
 * @type boolean
 *
 * @param disableInChoice
 * @desc 選択肢の表示中はウィンドウを非表示にできなくなります。
 * @default true
 * @type boolean
 *
 * @param restoreByDecision
 * @desc メッセージ消去時、決定動作により非表示になっていたメッセージウィンドウを再表示できます。
 * @default false
 * @type boolean
 *
 * @help Erase message window (and restore) when triggered
 *
 * This plugin is released under the MIT License.
 */
/*:ja
 * @plugindesc メッセージウィンドウ一時消去プラグイン
 * @author トリアコンタン
 *
 * @param triggerButton
 * @text ボタン名称
 * @desc ウィンドウを消去するボタンです。(複数登録可能) プラグイン等で入力可能なボタンを追加した場合は直接入力
 * @default ["Right-click"]
 * @type combo[]
 * @option 右クリック
 * @option shift
 * @option control
 * @option tab
 * @option pageup
 * @option pagedown
 * @option debug
 *
 * @param triggerSwitch
 * @text トリガースイッチ
 * @desc 指定したスイッチに連動させてウィンドウを消去します。並列処理などを使ってON/OFFを適切に管理してください。
 * @default 0
 * @type switch
 *
 * @param linkPictureNumbers
 * @text 連動ピクチャ番号
 * @desc ウィンドウ消去時に連動して不透明度を[0]にするピクチャの番号です。
 * @default []
 * @type number[]
 *
 * @param linkShowPictureNumbers
 * @text 連動表示ピクチャ番号
 * @desc ウィンドウ消去時に連動して不透明度を[255]にするピクチャの番号です。
 * @default []
 * @type number[]
 *
 * @param disableLinkSwitchId
 * @text 連動ピクチャ無効スイッチ
 * @desc 指定した番号のスイッチがONのとき、ピクチャの連動が無効になります。
 * @default 0
 * @type switch
 *
 * @param disableSwitchId
 * @text 無効スイッチ
 * @desc 指定した番号のスイッチがONのとき、プラグイン全体の機能が無効になります。
 * @default 0
 * @type switch
 *
 * @param disableInBattle
 * @text 戦闘中無効化
 * @desc trueのとき、戦闘中にプラグインの機能を無効にします。
 * @default false
 * @type boolean
 *
 * @param disableInChoice
 * @text 選択肢表示中は無効
 * @desc 選択肢の表示中はウィンドウを非表示にできなくなります。
 * @default true
 * @type boolean
 *
 * @param restoreByDecision
 * @text 決定動作で復帰
 * @desc メッセージ消去時、決定動作により非表示になっていたメッセージウィンドウを再表示できます。
 * @default false
 * @type boolean
 *
 * @help メッセージウィンドウを表示中に指定したボタンを押下することで
 * This will erase the message window. Press again to revert.
 *
 * You can specify a picture to become [0] opacity when erasing the window.
 * Specify this if you are using a specific picture as the background, for example.
 * When redisplayed, the opacity will be restored to the opacity before the window was hidden.
 *
 * The method of specifying parameters has been changed in part from version 2.0.0.
 * If you were using a previous version, please reconfigure.
 *
 * This plugin has no plugin commands.
 *
 * Terms of Use:
 *  Modification and redistribution without the author's consent are allowed,
 *  and there are no restrictions on usage (commercial, 18+ use, etc.).
 *  This plugin is now yours.
 */
(function() {
    'use strict';

    /**
     * Create plugin parameter. param[paramName] ex. param.commandPrefix
     * @param pluginName plugin name(EncounterSwitchConditions)
     * @returns {Object} Created parameter
     */
    var createPluginParameter = function(pluginName) {
        var paramReplacer = function(key, value) {
            if (value === 'null') {
                return value;
            }
            if (value[0] === '"' && value[value.length - 1] === '"') {
                return value;
            }
            try {
                return JSON.parse(value);
            } catch (e) {
                return value;
            }
        };
        var parameter     = JSON.parse(JSON.stringify(PluginManager.parameters(pluginName), paramReplacer));
        PluginManager.setParameters(pluginName, parameter);
        return parameter;
    };
    var param = createPluginParameter('MessageWindowHidden');

    //=============================================================================
    // Game_Picture
    // This will be linked to the visibility of the message window.
    //=============================================================================
    Game_Picture.prototype.linkWithMessageWindow = function(opacity) {
        this._opacity       = opacity;
        this._targetOpacity = opacity;
    };

    //=============================================================================
    // Window_Message
    // When the specified button is pressed, the window and sub-window will be hidden.
    //=============================================================================
    var _Window_Message_updateWait      = Window_Message.prototype.updateWait;
    Window_Message.prototype.updateWait = function() {
        if (!this.isClosed() && this.isTriggeredHidden() && this.isEnableInChoice()) {
            if (!this.isHidden()) {
                this.hideAllWindow();
            } else {
                this.showAllWindow();
            }
        } else if (this.isHidden() && this.isTriggered() && param.restoreByDecision) {
            this.showAllWindow();
            Input.update();
            TouchInput.update();
        }
        var wait = _Window_Message_updateWait.apply(this, arguments);
        if (this.isHidden() && this.visible) {
            this.hideAllWindow();
        }
        return wait;
    };

    Window_Message.prototype.isEnableInChoice = function() {
        return !(param.disableInChoice && $gameMessage.isChoice());
    };

    Window_Message.prototype.hideAllWindow = function() {
        this.hide();
        this.subWindows().forEach(function(subWindow) {
            this.hideSubWindow(subWindow);
        }.bind(this));
        if (this.hasNameWindow() && !this.nameWindowIsSubWindow()) this.hideSubWindow(this._nameWindow);
        this._originalPictureOpacities = {};
        this.linkPictures(0, param.linkPictureNumbers);
        this.linkPictures(255, param.linkShowPictureNumbers);
        this._hideByMessageWindowHidden = true;
    };

    Window_Message.prototype.showAllWindow = function() {
        this.show();
        this.subWindows().forEach(function(subWindow) {
            this.showSubWindow(subWindow);
        }.bind(this));
        if (this.hasNameWindow() && !this.nameWindowIsSubWindow()) this.showSubWindow(this._nameWindow);
        this.linkPictures(null, param.linkShowPictureNumbers);
        this.linkPictures(null, param.linkPictureNumbers);
        this._hideByMessageWindowHidden = false;
    };

    Window_Message.prototype.isHidden = function() {
        return this._hideByMessageWindowHidden;
    };

    Window_Message.prototype.linkPictures = function(opacity, pictureNumbers) {
        if (!pictureNumbers || $gameSwitches.value(param.disableLinkSwitchId)) {
            return;
        }
        pictureNumbers.forEach(function(pictureId) {
            this.linkPicture(opacity, pictureId);
        }, this);
    };

    Window_Message.prototype.linkPicture = function(opacity, pictureId) {
        var picture = $gameScreen.picture(pictureId);
        if (!picture) {
            return;
        }
        if (opacity === null) {
            if (!this._originalPictureOpacities.hasOwnProperty(pictureId)) {
                return;
            }
            opacity = this._originalPictureOpacities[pictureId];
        } else {
            this._originalPictureOpacities[pictureId] = picture.opacity();
        }
        picture.linkWithMessageWindow(opacity);
    };

    Window_Message.prototype.hideSubWindow = function(subWindow) {
        subWindow.prevVisible = subWindow.visible;
        subWindow.hide();
    };

    Window_Message.prototype.showSubWindow = function(subWindow) {
        if (subWindow.prevVisible) subWindow.show();
        subWindow.prevVisible = undefined;
    };

    Window_Message.prototype.hasNameWindow = function() {
        return this._nameWindow && typeof Window_NameBox !== 'undefined';
    };

    // In the old YEP_MessageCore.js, the name display window was included in subWindows.
    Window_Message.prototype.nameWindowIsSubWindow = function() {
        return this.subWindows().filter(function(subWindow) {
            return subWindow === this._nameWindow;
        }, this).length > 0;
    };

    Window_Message.prototype.disableWindowHidden = function () {
        return (param.disableSwitchId > 0 && $gameSwitches.value(param.disableSwitchId)) ||
            (param.disableInBattle && $gameParty.inBattle());
    };

    Window_Message.prototype.isTriggeredHidden = function() {
        if (this.disableWindowHidden()) {
            return false;
        }
        if (param.triggerSwitch > 0 && this.isTriggeredHiddenSwitch()) {
            return true;
        }
        return param.triggerButton.some(function(button) {
            switch (button) {
                case '':
                case 'Right-click':
                case 'light_click':
                    return TouchInput.isCancelled();
                case 'ok':
                    return false;
                default:
                    return Input.isTriggered(button);
            }
        });
    };

    Window_Message.prototype.isTriggeredHiddenSwitch = function() {
        var triggerSwitch = $gameSwitches.value(param.triggerSwitch);
        if (triggerSwitch && !this.isHidden()) {
            return true;
        }
        if (!triggerSwitch && this.isHidden()) {
            return true;
        }
        return false;
    };

    var _Window_Message_updateInput      = Window_Message.prototype.updateInput;
    Window_Message.prototype.updateInput = function() {
        if (this.isHidden()) return true;
        return _Window_Message_updateInput.apply(this, arguments);
    };

    //=============================================================================
    // Window_ChoiceList、Window_NumberInput、Window_EventItem
    //  While hidden, updates will be paused.
    //=============================================================================
    var _Window_ChoiceList_update      = Window_ChoiceList.prototype.update;
    Window_ChoiceList.prototype.update = function() {
        if (!this.visible) return;
        _Window_ChoiceList_update.apply(this, arguments);
    };

    var _Window_NumberInput_update      = Window_NumberInput.prototype.update;
    Window_NumberInput.prototype.update = function() {
        if (!this.visible) return;
        _Window_NumberInput_update.apply(this, arguments);
    };

    var _Window_EventItem_update      = Window_EventItem.prototype.update;
    Window_EventItem.prototype.update = function() {
        if (!this.visible) return;
        _Window_EventItem_update.apply(this, arguments);
    };
})();

