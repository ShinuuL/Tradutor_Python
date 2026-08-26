//=============================================================================
// CustomizeConfigDefault.js
// ----------------------------------------------------------------------------
// (C)2015 Triacontane
// This plugin is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
// 1.1.1 2020/09/13 Resolved inconsistency when used with Mano_InputConfig.js, where the Option item is not displayed.
// 1.1.0 2016/08/01 Added the functionality to hide items themselves.
// 1.0.3 2016/06/22 Multi-language support.
// 1.0.2 2016/01/17 Countermeasure for conflicts.
// 1.0.1 2015/11/01 Corrected the redefinition method of existing code (no changes in content).
// 1.0.0 2015/11/01 First Edition
// ----------------------------------------------------------------------------
// [Blog]   : https://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:
 * @plugindesc Setting default value for Options
 * @author triacontane
 *
 * @param AlwaysDash
 * @desc Always dash(ON/OFF)
 * @default OFF
 *
 * @param CommandRemember
 * @desc Command remember(ON/OFF)
 * @default OFF
 *
 * @param BgmVolume
 * @desc BGM Volume(0-100)
 * @default 100
 *
 * @param BgsVolume
 * @desc BGS Volume(0-100)
 * @default 100
 *
 * @param MeVolume
 * @desc ME Volume(0-100)
 * @default 100
 *
 * @param SeVolume
 * @desc SE Volume(0-100)
 * @default 100
 *
 * @param EraseAlwaysDash
 * @desc Erase AlwaysDash Option(ON/OFF)
 * @default OFF
 *
 * @param EraseCommandRemember
 * @desc Erase CommandRemember Option(ON/OFF)
 * @default OFF
 *
 * @param EraseBgmVolume
 * @desc Erase BgmVolume Option(ON/OFF)
 * @default OFF
 *
 * @param EraseBgsVolume
 * @desc Erase BgsVolume Option(ON/OFF)
 * @default OFF
 *
 * @param EraseMeVolume
 * @desc Erase MeVolume Option(ON/OFF)
 * @default OFF
 *
 * @param EraseSeVolume
 * @desc Erase SeVolume Option(ON/OFF)
 * @default OFF
 *
 * @help Setting default value for Options.
 *
 * This plugin is released under the MIT License.
 */
/*:ja
 * @plugindesc [基本設定]　オプションデフォルト値設定プラグイン
 * @author トリアコンタン
 *
 * @param 常時ダッシュ
 * @desc 常にダッシュする。（Shiftキーを押している場合のみ歩行）(ON/OFF)
 * @default OFF
 *
 * @param コマンド記憶
 * @desc 選択したコマンドを記憶する。(ON/OFF)
 * @default OFF
 *
 * @param BGM音量
 * @desc BGMの音量。0-100
 * @default 100
 *
 * @param BGS音量
 * @desc BGSの音量。0-100
 * @default 100
 *
 * @param ME音量
 * @desc MEの音量。0-100
 * @default 100
 *
 * @param SE音量
 * @desc SEの音量。0-100
 * @default 100
 *
 * @param 常時ダッシュ消去
 * @desc 常時ダッシュの項目を非表示にする。(ON/OFF)
 * @default OFF
 *
 * @param コマンド記憶消去
 * @desc コマンド記憶の項目を非表示にする。(ON/OFF)
 * @default OFF
 *
 * @param BGM音量消去
 * @desc BGM音量の項目を非表示にする。(ON/OFF)
 * @default OFF
 *
 * @param BGS音量消去
 * @desc BGS音量の項目を非表示にする。(ON/OFF)
 * @default OFF
 *
 * @param ME音量消去
 * @desc ME音量の項目を非表示にする。(ON/OFF)
 * @default OFF
 *
 * @param SE音量消去
 * @desc SE音量の項目を非表示にする。(ON/OFF)
 * @default OFF
 *
 * @help オプション画面で設定可能な項目のデフォルト値を指定した値に変更します。
 * For example, if you keep Dash ON from the first run,
 * you can save the player the trouble of changing the settings.
 * This process will only be executed if the config.rpgsave file does not exist.
 *
 * Additionally, you can remove the items themselves.
 * For example, in a game without battles, items like "Command Memory" can be removed.
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
    var pluginName = 'CustomizeConfigDefault';

    var getParamNumber = function(paramNames, min, max) {
        var value = getParamOther(paramNames);
        if (arguments.length < 2) min = -Infinity;
        if (arguments.length < 3) max = Infinity;
        return (parseInt(value, 10) || 0).clamp(min, max);
    };

    var getParamBoolean = function(paramNames) {
        var value = getParamOther(paramNames);
        return (value || '').toUpperCase() === 'ON';
    };

    var getParamOther = function(paramNames) {
        if (!Array.isArray(paramNames)) paramNames = [paramNames];
        for (var i = 0; i < paramNames.length; i++) {
            var name = PluginManager.parameters(pluginName)[paramNames[i]];
            if (name) return name;
        }
        return null;
    };

    //=============================================================================
    // Parameter Retrieval and Formatting
    //=============================================================================
    var paramAlwaysDash           = getParamBoolean(['AlwaysDash', 'Constant Dash']);
    var paramCommandRemember      = getParamBoolean(['CommandRemember', 'Command Memory']);
    var paramBgmVolume            = getParamNumber(['BgmVolume', 'BGM Volume'], 0, 100);
    var paramBgsVolume            = getParamNumber(['BgsVolume', 'BGS Volume'], 0, 100);
    var paramMeVolume             = getParamNumber(['MeVolume', 'ME Volume'], 0, 100);
    var paramSeVolume             = getParamNumber(['SeVolume', 'SE Volume'], 0, 100);
    var paramEraseAlwaysDash      = getParamBoolean(['EraseAlwaysDash', 'Permanent Dash Deletion']);
    var paramEraseCommandRemember = getParamBoolean(['EraseCommandRemember', 'Command Memory Deletion']);
    var paramEraseBgmVolume       = getParamBoolean(['EraseBgmVolume', 'BGM Volume Deletion']);
    var paramEraseBgsVolume       = getParamBoolean(['EraseBgsVolume', 'BGS Volume Deletion']);
    var paramEraseMeVolume        = getParamBoolean(['EraseMeVolume', 'ME Volume Deletion']);
    var paramEraseSeVolume        = getParamBoolean(['EraseSeVolume', 'SE volume off']);

    //=============================================================================
    // ConfigManager
    //  We assign initial values to each item.
    //=============================================================================
    var _ConfigManagerApplyData = ConfigManager.applyData;
    ConfigManager.applyData     = function(config) {
        _ConfigManagerApplyData.apply(this, arguments);
        if (config.alwaysDash == null)      this.alwaysDash = paramAlwaysDash;
        if (config.commandRemember == null) this.commandRemember = paramCommandRemember;
        if (config.bgmVolume == null)       this.bgmVolume = paramBgmVolume;
        if (config.bgsVolume == null)       this.bgsVolume = paramBgsVolume;
        if (config.meVolume == null)        this.meVolume = paramMeVolume;
        if (config.seVolume == null)        this.seVolume = paramSeVolume;
    };

    //=============================================================================
    // Window_Options
    //  We remove items with parameters set to blank.
    //=============================================================================
    var _Window_Options_makeCommandList = Window_Options.prototype.makeCommandList;
    Window_Options.prototype.makeCommandList = function() {
        _Window_Options_makeCommandList.apply(this, arguments);
        if (paramEraseAlwaysDash) this.eraseOption('alwaysDash');
        if (paramEraseCommandRemember) this.eraseOption('commandRemember');
        if (paramEraseBgmVolume) this.eraseOption('bgmVolume');
        if (paramEraseBgsVolume) this.eraseOption('bgsVolume');
        if (paramEraseMeVolume) this.eraseOption('meVolume');
        if (paramEraseSeVolume) this.eraseOption('seVolume');
    };

    Window_Options.prototype.eraseOption = function(symbol) {
        for (var i = 0; i < this._list.length; i++) {
            if (this._list[i].symbol === symbol) {
                this._list.splice(i, 1);
                // for Mano_InputConfig.js
                this.adjustIndexManoInputConfig(i);
                break;
            }
        }
    };

    Window_Options.prototype.adjustIndexManoInputConfig = function(index) {
        if (this._gamepadOptionIndex > index) {
            this._gamepadOptionIndex -= 1;
        }
        if (this._keyboardConfigIndex > index) {
            this._keyboardConfigIndex -= 1;
        }
    };
})();