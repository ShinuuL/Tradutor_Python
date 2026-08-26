//=============================================================================
// CustomizeConfigItem.js
// ----------------------------------------------------------------------------
// (C) 2015 Triacontane
// This software is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
// 2.4.0 2023/02/16 Fixed the ability to retrieve current settings via script
// 2.3.0 2021/12/21 Added the functionality to set whitespace for items
// 2.2.1 2021/08/05 Fixed an issue where the game would not function properly when adding hidden items while saving (by 柊菜緒)
// 2.2.0 2021/03/09 Modified to play the decision SE when the item is decided with a script specified
// 2.1.2 2020/10/13 Fixed a conflict where adding items other than the end would cause display inconsistencies when used with Mano_InputConfig.js
// 2.1.0 2017/12/15 Added the functionality to freely set the order of added items, including default items
//                  Item names localized to Japanese
// 2.0.1 2017/10/15 Fixed an issue where the game would crash upon starting when enabling switch items after 2.0.0 updates
// 2.0.0 2017/09/10 Added support for MZ's type specification feature, allowing multiple option items to be added arbitrarily
// 1.2.3 2017/06/08 Fixed an issue where the game would no longer launch after 1.2.2 updates
// 1.2.2 2017/05/27 Refactored potential competitive description (property addition to Object class)
// 1.2.1 2016/12/08 Fixed the issue where pressing the confirm button with default items after 1.2.0 functionality changes would result in an error
// 1.2.0 2016/12/02 Added a feature to set scripts that run when the confirm button is pressed for each item
// 1.1.1 2016/08/14 Fixed the issue where initial values for switch and volume items were set to invalid
// 1.1.0 2016/04/29 Modified so that item values cycle when clicked
// 1.0.0 2016/01/17 Initial release
// ----------------------------------------------------------------------------
// [Blog]   : http://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:
 * @plugindesc オプション任意項目作成プラグイン
 * @author トリアコンタン
 *
 * @param 数値項目
 * @desc 追加する数値項目のオプション項目情報です。
 * @default
 * @type struct<NumberData>[]
 *
 * @param 文字項目
 * @desc 追加する文字項目のオプション項目情報です。
 * @default
 * @type struct<StringData>[]
 *
 * @param スイッチ項目
 * @desc 追加するスイッチ項目のオプション項目情報です。
 * @default
 * @type struct<BooleanData>[]
 *
 * @param 音量項目
 * @desc 追加する音量項目のオプション項目情報です。
 * @default
 * @type struct<VolumeData>[]
 *
 * @help オプション画面に任意の項目を追加します。
 * There are four types of items.
 * Set the value to empty for unnecessary items.
 *
 * - Switch item:
 * An item to select ON/OFF. The value will synchronize with the specified switch number.
 * Setting values from the options will reflect on the switch, and
 * changing the switch will reflect in the option's value.
 * Furthermore, the value is shared between save data.
 * Setting a hidden flag will cause it to no longer appear on the option screen.
 * Can be used for items that do not appear until the game progresses.
 * Hidden flags can be removed via plugin commands.
 *
 * Scripts are advanced items. Aim at the target with your cursor and press the confirm button.
 * Pressing this will execute the specified JavaScript.
 * Primarily used for navigating to dedicated setting screens, etc.
 *
 * - Numerical items:
 * This is a selection item for numbers. The specified number's variable and value will synchronize.
 * In switch items, specify the content in addition to
 * minimum and maximum values as well as the value that changes per input.
 *
 * • Volume item：
 * This is a selection item for volume. Use it for character-specific voice volumes, similar to BGM volume settings.
 *
 *
 * • Text item：
 * This is a selection item for text. Select from an array of specified characters.
 * The index of the selected character (with a starting position of 0) will be set to the variable.
 * The initial value set will also be an index.
 *
 * Plugin command details
 *  Execute via the event command "Plugin Command".
 *  (Separate parameters with a space)
 *
 *  CC_UNLOCK or
 *  オプション任意項目の隠し解除 [項目名]
 *  　Removes the hidden flag from the specified item.
 *  Example usage: CC_UNLOCK Numeric Item 1
 *
 * Terms of Use:
 *  Modification and redistribution without the author's consent are allowed,
 *  and there are no restrictions on usage (commercial, 18+ use, etc.).
 *  This plugin is now yours.
 */

/*~struct~NumberData:
 * @param Name
 * @text 項目名称
 * @desc 項目の名称です。
 * @default 数値項目1
 *
 * @param DefaultValue
 * @text 初期値
 * @desc 項目の初期値です。
 * @default 0
 * @type number
 *
 * @param VariableID
 * @text 変数番号
 * @desc 項目の設定内容が格納される変数番号です。
 * @default 0
 * @type variable
 *
 * @param HiddenFlag
 * @text 隠しフラグ
 * @desc 項目がデフォルトで隠されるようになります。プラグインコマンドの実行で表示されます。
 * @default false
 * @type boolean
 *
 * @param Script
 * @text スクリプト
 * @desc 項目を決定したときに実行されるスクリプトです。
 * @default
 *
 * @param NumberMin
 * @text 最小値
 * @desc 項目の最小値です。
 * @default 0
 * @type number
 *
 * @param NumberMax
 * @text 最大値
 * @desc 項目の最大値です。
 * @default 100
 * @type number
 *
 * @param NumberStep
 * @text 変化値
 * @desc 項目を操作したときの数値の変化量です。
 * @default 20
 * @type number
 *
 * @param AddPosition
 * @text 追加位置
 * @desc 項目を追加する位置です。指定した項目の上に追加されます。
 * @default
 * @type select
 * @option 末尾に追加
 * @value
 * @option 常時ダッシュ
 * @value alwaysDash
 * @option コマンド記憶
 * @value commandRemember
 * @option BGM 音量
 * @value bgmVolume
 * @option BGS 音量
 * @value bgsVolume
 * @option ME 音量
 * @value meVolume
 * @option SE 音量
 * @value seVolume
 *
 * @param PaddingTop
 * @text 余白
 * @desc 項目の上の余白ピクセル数です。項目の間隔を開けたいときに指定します。
 * @default 0
 * @type number
 */
/*~struct~BooleanData:
 * @param Name
 * @text 項目名称
 * @desc 項目の名称です。
 * @default スイッチ項目1
 *
 * @param DefaultValue
 * @text 初期値
 * @desc 項目の初期値です。
 * @default false
 * @type boolean
 *
 * @param SwitchID
 * @text スイッチ番号
 * @desc 項目の設定内容が格納されるスイッチ番号です。
 * @default 0
 * @type switch
 *
 * @param HiddenFlag
 * @text 隠しフラグ
 * @desc 項目がデフォルトで隠されるようになります。プラグインコマンドの実行で表示されます。
 * @default false
 * @type boolean
 *
 * @param Script
 * @text スクリプト
 * @desc 項目を決定したときに実行されるスクリプトです。
 * @default
 *
 * @param AddPosition
 * @text 追加位置
 * @desc 項目を追加する位置です。指定した項目の上に追加されます。
 * @default
 * @type select
 * @option 末尾に追加
 * @value
 * @option 常時ダッシュ
 * @value alwaysDash
 * @option コマンド記憶
 * @value commandRemember
 * @option BGM 音量
 * @value bgmVolume
 * @option BGS 音量
 * @value bgsVolume
 * @option ME 音量
 * @value meVolume
 * @option SE 音量
 * @value seVolume
 *
 * @param PaddingTop
 * @text 余白
 * @desc 項目の上の余白ピクセル数です。項目の間隔を開けたいときに指定します。
 * @default 0
 * @type number
 */
/*~struct~StringData:
 * @param Name
 * @text 項目名称
 * @desc 項目の名称です。
 * @default 文字列項目1
 *
 * @param DefaultValue
 * @text 初期値
 * @desc 項目の初期値です。インデックスの数値を指定します。
 * @default 0
 * @type number
 *
 * @param VariableID
 * @text 変数番号
 * @desc 項目の設定内容が格納される変数番号です。
 * @default 0
 * @type variable
 *
 * @param HiddenFlag
 * @text 隠しフラグ
 * @desc 項目がデフォルトで隠されるようになります。プラグインコマンドの実行で表示されます。
 * @default false
 * @type boolean
 *
 * @param Script
 * @text スクリプト
 * @desc 項目を決定したときに実行されるスクリプトです。
 * @default
 *
 * @param StringItems
 * @text 内容の配列
 * @desc 項目の設定内容の配列です。
 * @default
 * @type string[]
 *
 * @param AddPosition
 * @text 追加位置
 * @desc 項目を追加する位置です。指定した項目の上に追加されます。
 * @default
 * @type select
 * @option 末尾に追加
 * @value
 * @option 常時ダッシュ
 * @value alwaysDash
 * @option コマンド記憶
 * @value commandRemember
 * @option BGM 音量
 * @value bgmVolume
 * @option BGS 音量
 * @value bgsVolume
 * @option ME 音量
 * @value meVolume
 * @option SE 音量
 * @value seVolume
 *
 * @param PaddingTop
 * @text 余白
 * @desc 項目の上の余白ピクセル数です。項目の間隔を開けたいときに指定します。
 * @default 0
 * @type number
 */
/*~struct~VolumeData:
 * @param Name
 * @text 項目名称
 * @desc 項目の名称です。
 * @default 音量項目1
 *
 * @param DefaultValue
 * @text 初期値
 * @desc 項目の初期値です。
 * @default 0
 * @type number
 *
 * @param VariableID
 * @text 変数番号
 * @desc 項目の設定内容が格納される変数番号です。
 * @default 0
 * @type variable
 *
 * @param HiddenFlag
 * @text 隠しフラグ
 * @desc 項目がデフォルトで隠されるようになります。プラグインコマンドの実行で表示されます。
 * @default false
 * @type boolean
 *
 * @param Script
 * @text スクリプト
 * @desc 項目を決定したときに実行されるスクリプトです。変数[value]で現在の選択値が参照できます。
 * @default
 *
 * @param AddPosition
 * @text 追加位置
 * @desc 項目を追加する位置です。指定した項目の上に追加されます。
 * @default
 * @type select
 * @option 末尾に追加
 * @value
 * @option 常時ダッシュ
 * @value alwaysDash
 * @option コマンド記憶
 * @value commandRemember
 * @option BGM 音量
 * @value bgmVolume
 * @option BGS 音量
 * @value bgsVolume
 * @option ME 音量
 * @value meVolume
 * @option SE 音量
 * @value seVolume
 *
 * @param PaddingTop
 * @text 余白
 * @desc 項目の上の余白ピクセル数です。項目の間隔を開けたいときに指定します。
 * @default 0
 * @type number
 */

(function() {
    'use strict';
    var pluginName = 'CustomizeConfigItem';

    var getParamString = function(paramNames) {
        var value = getParamOther(paramNames);
        return value == null ? '' : value;
    };

    var getParamOther = function(paramNames) {
        if (!Array.isArray(paramNames)) paramNames = [paramNames];
        for (var i = 0; i < paramNames.length; i++) {
            var name = PluginManager.parameters(pluginName)[paramNames[i]];
            if (name) return name;
        }
        return null;
    };

    var getParamArrayJson = function(paramNames, defaultValue) {
        var value = getParamString(paramNames) || null;
        try {
            value = JSON.parse(value);
            if (value === null) {
                value = defaultValue;
            } else {
                value = value.map(function(valueData) {
                    return JSON.parse(valueData);
                });
            }
        } catch (e) {
            alert(`!!!Plugin param is wrong.!!!\nPlugin:${pluginName}.js\nName:[${paramNames}]\nValue:${value}`);
            value = defaultValue;
        }
        return value;
    };

    var getCommandName = function(command) {
        return (command || '').toUpperCase();
    };

    var getArgNumber = function(arg, min, max) {
        if (arguments.length < 2) min = -Infinity;
        if (arguments.length < 3) max = Infinity;
        return (parseInt(arg) || 0).clamp(min, max);
    };

    var getArgBoolean = function(arg) {
        return (arg || '').toUpperCase() === 'TRUE';
    };

    var getArgJson = function(arg, defaultValue) {
        try {
            arg = JSON.parse(arg || null);
            if (arg === null) {
                arg = defaultValue;
            }
        } catch (e) {
            alert(`!!!Plugin param is wrong.!!!\nPlugin:${pluginName}.js\nValue:${arg}`);
            arg = defaultValue;
        }
        return arg;
    };

    var iterate = function(that, handler) {
        Object.keys(that).forEach(function(key, index) {
            handler.call(that, key, that[key], index);
        });
    };

    //=============================================================================
    // Parameter Retrieval and Formatting
    //=============================================================================
    var param           = {};
    param.numberOptions = getParamArrayJson(['NumberOptions', 'Numeric Item'], []);
    param.stringOptions = getParamArrayJson(['StringOptions', 'Text Item'], []);
    param.switchOptions = getParamArrayJson(['SwitchOptions', 'Switch Item'], []);
    param.volumeOptions = getParamArrayJson(['VolumeOptions', 'Volume item'], []);

    var localOptionWindowIndex = 0;

    //=============================================================================
    // Game_Interpreter
    //  Define additional plugin commands.
    //=============================================================================
    var _Game_Interpreter_pluginCommand      = Game_Interpreter.prototype.pluginCommand;
    Game_Interpreter.prototype.pluginCommand = function(command, args) {
        _Game_Interpreter_pluginCommand.call(this, command, args);
        this.pluginCommandCustomizeConfigItem(command, args);
    };

    Game_Interpreter.prototype.pluginCommandCustomizeConfigItem = function(command, args) {
        switch (getCommandName(command)) {
            case 'CC_UNLOCK' :
            case 'Unhide optional hidden item' :
                ConfigManager.customParamUnlock(args[0]);
                break;
        }
    };

    //=============================================================================
    // ConfigManager
    //  Manages settings and initial values for additional items.
    //=============================================================================
    ConfigManager.customParams   = null;
    ConfigManager.hiddenInfo     = {};
    ConfigManager._symbolNumber  = 'Number';
    ConfigManager._symbolBoolean = 'Boolean';
    ConfigManager._symbolString  = 'String';
    ConfigManager._symbolVolume  = 'Volume';

    ConfigManager.getCustomParams = function() {
        if (this.customParams) {
            return this.customParams;
        }
        this.customParams = {};
        param.numberOptions.forEach(function(optionItem, index) {
            this.makeNumberOption(optionItem, index);
        }, this);
        param.stringOptions.forEach(function(optionItem, index) {
            this.makeStringOption(optionItem, index);
        }, this);
        param.switchOptions.forEach(function(optionItem, index) {
            this.makeSwitchOption(optionItem, index);
        }, this);
        param.volumeOptions.forEach(function(optionItem, index) {
            this.makeVolumeOption(optionItem, index);
        }, this);
        return this.customParams;
    };

    ConfigManager.makeNumberOption = function(optionItem, index) {
        var data    = this.makeCommonOption(optionItem, index, this._symbolNumber);
        data.min    = getArgNumber(optionItem.NumberMin);
        data.max    = getArgNumber(optionItem.NumberMax);
        data.offset = getArgNumber(optionItem.NumberStep);
        this.pushOptionData(data);
    };

    ConfigManager.makeStringOption = function(optionItem, index) {
        var data    = this.makeCommonOption(optionItem, index, this._symbolString);
        data.values = getArgJson(optionItem.StringItems, ['no item']);
        data.min    = 0;
        data.max    = data.values.length - 1;
        this.pushOptionData(data);
    };

    ConfigManager.makeSwitchOption = function(optionItem, index) {
        var data       = this.makeCommonOption(optionItem, index, this._symbolBoolean);
        data.initValue = getArgBoolean(optionItem.DefaultValue);
        data.variable  = getArgNumber(optionItem.SwitchID);
        this.pushOptionData(data);
    };

    ConfigManager.makeVolumeOption = function(optionItem, index) {
        var data = this.makeCommonOption(optionItem, index, this._symbolVolume);
        this.pushOptionData(data);
    };

    ConfigManager.makeCommonOption = function(optionItem, index, type) {
        var data       = {};
        data.symbol    = `${type}${index + 1}`;
        data.name      = optionItem.Name;
        data.hidden    = getArgBoolean(optionItem.HiddenFlag);
        data.script    = optionItem.Script;
        data.initValue = getArgNumber(optionItem.DefaultValue);
        data.variable  = getArgNumber(optionItem.VariableID, 0);
        data.addPotion = optionItem.AddPosition;
        data.padding   = getArgNumber(optionItem.PaddingTop);
        return data;
    };

    ConfigManager.pushOptionData = function(data) {
        this.customParams[data.symbol] = data;
    };

    var _ConfigManager_makeData = ConfigManager.makeData;
    ConfigManager.makeData      = function() {
        var config        = _ConfigManager_makeData.apply(this, arguments);
        config.hiddenInfo = {};
        iterate(this.getCustomParams(), function(symbol) {
            config[symbol]            = this[symbol];
            config.hiddenInfo[symbol] = this.hiddenInfo[symbol];
        }.bind(this));
        return config;
    };

    var _ConfigManager_applyData = ConfigManager.applyData;
    ConfigManager.applyData      = function(config) {
        _ConfigManager_applyData.apply(this, arguments);
        iterate(this.getCustomParams(), function(symbol, item) {
            if (symbol.contains(this._symbolBoolean)) {
                this[symbol] = this.readFlagCustom(config, symbol, item);
            } else if (symbol.contains(this._symbolVolume)) {
                this[symbol] = this.readVolumeCustom(config, symbol, item);
            } else {
                this[symbol] = this.readOther(config, symbol, item);
            }
            if (config.hiddenInfo) {
                this.hiddenInfo[symbol] = (typeof config.hiddenInfo[symbol] === 'boolean' ? config.hiddenInfo[symbol] : item.hidden);
            } else {
                this.hiddenInfo[symbol] = item.hidden;
            }
        }.bind(this));
    };

    ConfigManager.customParamUnlock = function(name) {
        iterate(this.getCustomParams(), function(symbol, item) {
            if (item.name === name) this.hiddenInfo[symbol] = false;
        }.bind(this));
        this.save();
    };

    ConfigManager.readOther = function(config, name, item) {
        var value = config[name];
        if (value !== undefined) {
            return Number(value).clamp(item.min, item.max);
        } else {
            return item.initValue;
        }
    };

    ConfigManager.readFlagCustom = function(config, name, item) {
        if (config[name] !== undefined) {
            return this.readFlag(config, name);
        } else {
            return item.initValue;
        }
    };

    ConfigManager.readVolumeCustom = function(config, name, item) {
        if (config[name] !== undefined) {
            return this.readVolume(config, name);
        } else {
            return item.initValue;
        }
    };

    ConfigManager.exportCustomParams = function() {
        if (!$gameVariables || !$gameSwitches) return;
        iterate(this.getCustomParams(), function(symbol, item) {
            if (item.variable > 0) {
                if (symbol.contains(this._symbolBoolean)) {
                    $gameSwitches.setValue(item.variable, !!this[symbol]);
                } else {
                    $gameVariables.setValue(item.variable, this[symbol]);
                }
            }
        }.bind(this));
    };

    ConfigManager.importCustomParams = function() {
        if (!$gameVariables || !$gameSwitches) return;
        iterate(this.getCustomParams(), function(symbol, item) {
            if (item.variable > 0) {
                if (symbol.contains(this._symbolBoolean)) {
                    this[symbol] = $gameSwitches.value(item.variable);
                } else if (symbol.contains(this._symbolVolume)) {
                    this[symbol] = $gameVariables.value(item.variable).clamp(0, 100);
                } else {
                    this[symbol] = $gameVariables.value(item.variable).clamp(item.min, item.max);
                }
            }
        }.bind(this));
    };

    var _ConfigManager_save = ConfigManager.save;
    ConfigManager.save      = function() {
        _ConfigManager_save.apply(this, arguments);
        this.exportCustomParams();
    };

    //=============================================================================
    // Game_Map
    //  Synchronizes option values during refresh.
    //=============================================================================
    var _Game_Map_refresh      = Game_Map.prototype.refresh;
    Game_Map.prototype.refresh = function() {
        _Game_Map_refresh.apply(this, arguments);
        ConfigManager.importCustomParams();
    };

    //=============================================================================
    // DataManager
    //  Synchronizes option values during save and load.
    //=============================================================================
    var _DataManager_setupNewGame = DataManager.setupNewGame;
    DataManager.setupNewGame      = function() {
        _DataManager_setupNewGame.apply(this, arguments);
        ConfigManager.exportCustomParams();
    };

    var _DataManager_loadGameWithoutRescue = DataManager.loadGameWithoutRescue;
    DataManager.loadGameWithoutRescue      = function(savefileId) {
        var result = _DataManager_loadGameWithoutRescue.apply(this, arguments);
        ConfigManager.exportCustomParams();
        return result;
    };

    //=============================================================================
    // Window_Options
    //  Drawing additional items.
    //=============================================================================
    var _Window_Options_initialize      = Window_Options.prototype.initialize;
    Window_Options.prototype.initialize = function() {
        this._customParams = ConfigManager.getCustomParams();
        _Window_Options_initialize.apply(this, arguments);
        this.select(localOptionWindowIndex);
        localOptionWindowIndex = 0;
    };

    var _Window_Options_itemRect = Window_Options.prototype.itemRect;
    Window_Options.prototype.itemRect = function(index) {
        var rect = _Window_Options_itemRect.apply(this, arguments);
        rect.y += this.findAdditionalHeight(index);
        return rect;
    };

    Window_Options.prototype.findAdditionalHeight = function(index) {
        return this._list.reduce(function(prev, item, itemIndex) {
            return prev + (itemIndex <= index && item.ext ? item.ext : 0);
        }, 0);
    };

    var _Window_Options_makeCommandList      = Window_Options.prototype.makeCommandList;
    Window_Options.prototype.makeCommandList = function() {
        _Window_Options_makeCommandList.apply(this, arguments);
        this.addCustomOptions();
    };

    Window_Options.prototype.addCustomOptions = function() {
        iterate(this._customParams, function(key, item) {
            if (!ConfigManager.hiddenInfo[key]) {
                this.addCommand(item.name, key, undefined, item.padding);
                if (item.addPotion) {
                    this.shiftCustomOptions(item.addPotion);
                }
            }
        }.bind(this));
    };

    Window_Options.prototype.shiftCustomOptions = function(addPotion) {
        var targetCommand = this._list.filter(function(command) {
            return command.symbol === addPotion;
        })[0];
        if (!targetCommand) {
            return;
        }
        var targetIndex = this._list.indexOf(targetCommand);
        var newCommand = this._list.pop();
        this.addIndexForManoInputConfig(targetIndex);
        this._list.splice(targetIndex, 0, newCommand);
    };

    Window_Options.prototype.addIndexForManoInputConfig = function(index) {
        if (this._gamepadOptionIndex > index) {
            this._gamepadOptionIndex += 1;
        }
        if (this._keyboardConfigIndex > index) {
            this._keyboardConfigIndex += 1;
        }
    };

    var _Window_Options_statusText      = Window_Options.prototype.statusText;
    Window_Options.prototype.statusText = function(index) {
        var result = _Window_Options_statusText.apply(this, arguments);
        var symbol = this.commandSymbol(index);
        var value  = this.getConfigValue(symbol);
        if (this.isNumberSymbol(symbol)) {
            result = this.numberStatusText(value);
        } else if (this.isStringSymbol(symbol)) {
            result = this.stringStatusText(value, symbol);
        }
        return result;
    };

    Window_Options.prototype.isNumberSymbol = function(symbol) {
        return symbol.contains(ConfigManager._symbolNumber);
    };

    Window_Options.prototype.isStringSymbol = function(symbol) {
        return symbol.contains(ConfigManager._symbolString);
    };

    Window_Options.prototype.isCustomSymbol = function(symbol) {
        return !!this._customParams[symbol];
    };

    Window_Options.prototype.numberStatusText = function(value) {
        return value;
    };

    Window_Options.prototype.stringStatusText = function(value, symbol) {
        return this._customParams[symbol].values[value];
    };

    var _Window_Options_processOk      = Window_Options.prototype.processOk;
    Window_Options.prototype.processOk = function() {
        if (!this._shiftValue(1, true)) _Window_Options_processOk.apply(this, arguments);
        this.execScript();
    };

    var _Window_Options_cursorRight      = Window_Options.prototype.cursorRight;
    Window_Options.prototype.cursorRight = function(wrap) {
        if (!this._shiftValue(1, false)) _Window_Options_cursorRight.apply(this, arguments);
        this.execScript();
    };

    var _Window_Options_cursorLeft      = Window_Options.prototype.cursorLeft;
    Window_Options.prototype.cursorLeft = function(wrap) {
        if (!this._shiftValue(-1, false)) _Window_Options_cursorLeft.apply(this, arguments);
        this.execScript();
    };

    Window_Options.prototype._shiftValue = function(sign, loopFlg) {
        var symbol = this.commandSymbol(this.index());
        var value  = this.getConfigValue(symbol);
        if (this.isNumberSymbol(symbol)) {
            value += this.numberOffset(symbol) * sign;
            this.changeValue(symbol, this._clampValue(value, symbol, loopFlg));
            return true;
        }
        if (this.isStringSymbol(symbol)) {
            value += sign;
            this.changeValue(symbol, this._clampValue(value, symbol, loopFlg));
            return true;
        }
        return false;
    };

    Window_Options.prototype.execScript = function() {
        var symbol = this.commandSymbol(this.index());
        if (!this.isCustomSymbol(symbol)) return;
        var script = this._customParams[symbol].script;
        var value = this.getConfigValue(symbol);
        if (script) {
            eval(script);
            SoundManager.playOk();
        }
        localOptionWindowIndex = this.index();
    };

    Window_Options.prototype._clampValue = function(value, symbol, loopFlg) {
        var maxValue = this._customParams[symbol].max;
        var minValue = this._customParams[symbol].min;
        if (loopFlg) {
            if (value > maxValue) value = minValue;
            if (value < minValue) value = maxValue;
        }
        return value.clamp(this._customParams[symbol].min, this._customParams[symbol].max);
    };

    Window_Options.prototype.numberOffset = function(symbol) {
        var value = this._customParams[symbol].offset;
        if (Input.isPressed('shift')) value *= 10;
        return value;
    };

    Window_Options.prototype.windowHeight = function() {
        var height = this.fittingHeight(Math.min(this.numVisibleRows(), 14));
        return height + this.findAdditionalHeight(this.maxItems());
    };
})();

