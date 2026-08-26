//=============================================================================
// AnotherNewGame.js
// ----------------------------------------------------------------------------
// (C) 2015 Triacontane
// This plugin is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
// 3.0.1 2022/11/08 When initial commands and non-initial commands are mixed, a specific condition causes initial display commands to disappear. This issue has been fixed.
// 3.0.0 2020/03/08 Multiple "Another New Game" commands can now be registered. This version is not compatible with previous versions.
// 2.0.0 2019/03/19 Added a feature to start from the save location without moving the player when loading "Another Load".
//                  Added a switch that turns on automatically when loading "Another New Game".
//                  Added support for specifying parameter types.
// 1.4.0 2017/06/18 Added a feature to specify the additional position for "Another New Game".
// 1.3.0 2017/05/27 Added a feature to hide the New Game option.
// 1.2.4 2017/05/23 Corrected the plugin command help.
// 1.2.3 2017/01/25 Added a management number to avoid duplicate settings when publishing multiple games with the same plugin on the same server.
// 1.2.2 2016/12/10 Fixed an issue where, when loading "Another Load", the next event would start even if an event was running at the time of loading.
// 1.2.1 2016/11/23 Add settings to coordinate with the distant view title plugin (ParallaxTitle.js)
// 1.2.0 2016/11/22 Add a setting to prevent fade-out when selecting another new game
// 1.1.0 2016/03/29 Reflect code provided by fftfantt, adding a feature to load existing save files when selecting another new game
//                  during selection of an alternate new game
// 1.0.1 2015/11/10 Fix an issue where saving was no longer possible while applying the plugin
// 1.0.0 2015/11/07 Initial release
// ----------------------------------------------------------------------------
// [Blog]   : https://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:
 * @plugindesc アナザーニューゲーム追加プラグイン
 * @author トリアコンタン
 *
 * @param anotherDataList
 * @text アナザーニューゲームリスト
 * @desc アナザーニューゲームのコマンド一覧です。
 * @default []
 * @type struct<COMMAND>[]
 *
 * @param manageNumber
 * @text 管理番号
 * @desc 同一サーバ内に複数のゲームを配布する場合のみ、ゲームごとに異なる値を設定してください。(RPGアツマールは対象外)
 * @default
 *
 * @help バージョン3.0.0は以前のバージョンと互換性がありません。
 *
 * Add another new game option at the bottom of the title screen window.
 * Selecting it will transition to a specified map different from the new game.
 * It can be used for various purposes such as additional rewards after clearing, CG recall mode, staff credits, mini-games, hidden elements, etc.
 * Depending on how you use it.
 *
 * The options can be set to be initially hidden or unselectable.
 * These can be removed via plugin commands, and the removal state is shared across the entire game beyond save files.
 * You can also re-enable the previously disabled state.
 *
 * Settings are saved in the file "AnotherNewGameMk2.rpgsave".
 *
 * Plugin command details
 *   Execute the event command "Plugin Command".
 *
 *  ANG_VISIBLE 1  # [1]番目のアナザーニューゲームを表示にする。
 *  ANG_ENABLE 1   # [1]番目のアナザーニューゲームを選択可能にする。
 *  ANG_HIDDEN 1   # [1]番目のアナザーニューゲームを非表示にする。
 *  ANG_DISABLE 1  # [1]番目のアナザーニューゲームを選択禁止にする。
 *
 * Example (when you want to "Show" the first registered Another New Game)
 * ANG_VISIBLE 1
 *
 *  ANG_NEWGAME_HIDDEN  # Hide the New Game.
 *  ANG_NEWGAME_VISIBLE # Show the New Game.
 *
 * Be cautious when using the function to hide the New Game,
 * as it may prevent the game from starting.
 *
 * Terms of Use:
 *  Modification and redistribution without the author's consent are allowed,
 *  and there are no restrictions on usage (commercial, 18+ use, etc.).
 *  This plugin is now yours.
 */

/*~struct~COMMAND:
 * @param name
 * @text コマンド名称
 * @desc タイトル画面に表示されるコマンド名です。
 * @default Another New Game
 *
 * @param mapId
 * @text マップID
 * @desc 移動先のマップIDです。0を指定した場合、場所移動しません。
 * @default 1
 * @type number
 *
 * @param mapX
 * @text X座標
 * @desc 移動先のX座標です。
 * @default 1
 * @type number
 *
 * @param mapY
 * @text Y座標
 * @desc 移動先のY座標です。（自然数）
 * @default 1
 * @type number
 *
 * @param hidden
 * @text デフォルト非表示
 * @desc デフォルトで選択肢を非表示にします。プラグインコマンドで有効化できます。
 * @default false
 * @type boolean
 *
 * @param disable
 * @text デフォルト使用禁止
 * @desc デフォルトで選択肢を選択禁止にします。プラグインコマンドで有効化できます。
 * @default false
 * @type boolean
 *
 * @param addPosition
 * @text 追加位置
 * @desc アナザーニューゲームのコマンド追加位置です。(1:ニューゲームの上、2:コンティニューの上、3:オプションの上)
 * @default 0
 * @type select
 * @option オプションの下
 * @value 0
 * @option ニューゲームの上
 * @value 1
 * @option コンティニューの上
 * @value 2
 * @option オプションの上
 * @value 3
 *
 * @param switchId
 * @text 連動スイッチ番号
 * @desc アナザーニューゲーム開始時に自動でONになるスイッチを指定できます。
 * @default 0
 * @type switch
 *
 * @param fileLoad
 * @text ファイルロード
 * @desc アナザーニューゲーム選択時に、ロード画面に遷移して既存セーブデータをロードします。
 * @default false
 * @type boolean
 *
 * @param noFadeout
 * @text フェードアウト無効
 * @desc アナザーニューゲーム選択時に、オーディオや画面がフェードアウトしなくなります。
 * @default false
 * @type boolean
 */

(function() {
    var localExtraStageIndex = -1;

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
    var parameters = createPluginParameter('AnotherNewGame');
    parameters.anotherDataList = parameters.anotherDataList || [];

    /**
     * Convert escape characters.(require any window object)
     * @param text Target text
     * @returns {String} Converted text
     */
    var convertEscapeCharacters = function(text) {
        var windowLayer = SceneManager._scene._windowLayer;
        return windowLayer ? windowLayer.children[0].convertEscapeCharacters(text.toString()) : text;
    };

    var _Game_Interpreter_pluginCommand      = Game_Interpreter.prototype.pluginCommand;
    Game_Interpreter.prototype.pluginCommand = function(command, args) {
        _Game_Interpreter_pluginCommand.call(this, command, args);
        var index = args[0] ? parseInt(convertEscapeCharacters(args[0])) - 1 : 0;
        switch (command.toUpperCase()) {
            case 'ANG_VISIBLE' :
                ANGSettingManager.setVisible(index, true);
                ANGSettingManager.save();
                break;
            case 'ANG_ENABLE' :
                ANGSettingManager.setEnable(index, true);
                ANGSettingManager.save();
                break;
            case 'ANG_HIDDEN' :
                ANGSettingManager.setVisible(index, false);
                ANGSettingManager.save();
                break;
            case 'ANG_DISABLE' :
                ANGSettingManager.setEnable(index, false);
                ANGSettingManager.save();
                break;
            case 'ANG_NEWGAME_HIDDEN' :
                ANGSettingManager.newGameHidden = true;
                ANGSettingManager.save();
                break;
            case 'ANG_NEWGAME_VISIBLE' :
                ANGSettingManager.newGameHidden = false;
                ANGSettingManager.save();
                break;
        }
    };

    //=============================================================================
    // Game_Map
    //  Interrupts events that were executed when loading the Another New Game.
    //=============================================================================
    Game_Map.prototype.abortInterpreter = function() {
        if (this.isEventRunning()) {
            this._interpreter.command115();
        }
    };

    //=============================================================================
    // Scene_Title
    //  Additional definition for the process when selecting Another New Game.
    //=============================================================================
    var _Scene_Title_create      = Scene_Title.prototype.create;
    Scene_Title.prototype.create = function() {
        ANGSettingManager.loadData();
        _Scene_Title_create.call(this);
    };

    var _Scene_Title_commandContinue      = Scene_Title.prototype.commandContinue;
    Scene_Title.prototype.commandContinue = function() {
        _Scene_Title_commandContinue.call(this);
        localExtraStageIndex = -1;
    };

    var _Scene_Title_commandNewGameSecond      = Scene_Title.prototype.commandNewGameSecond;
    Scene_Title.prototype.commandNewGameSecond = function(index) {
        if (_Scene_Title_commandNewGameSecond) {
            _Scene_Title_commandNewGameSecond.apply(this, arguments);
        }
        var command = parameters.anotherDataList[index];
        if (command.noFadeout) {
            this._noFadeout = true;
        }
        if (!command.fileLoad) {
            var preMapId  = $dataSystem.startMapId;
            var preStartX = $dataSystem.startX;
            var preStartY = $dataSystem.startY;
            var newMapId  = command.mapId;
            if (newMapId > 0) {
                $dataSystem.startMapId = newMapId;
                $dataSystem.startX     = command.mapX || 1;
                $dataSystem.startY     = command.mapY || 1;
            }
            this.commandNewGame();
            $dataSystem.startMapId = preMapId;
            $dataSystem.startX     = preStartX;
            $dataSystem.startY     = preStartY;
            var switchId = command.switchId;
            if (switchId > 0) {
                $gameSwitches.setValue(switchId, true);
            }
        } else {
            this.commandContinue();
            localExtraStageIndex = index;
        }
    };

    var _Scene_Title_createCommandWindow      = Scene_Title.prototype.createCommandWindow;
    Scene_Title.prototype.createCommandWindow = function() {
        _Scene_Title_createCommandWindow.call(this);
        parameters.anotherDataList.forEach(function(command, index) {
            if (ANGSettingManager.isVisible(index)) {
                this._commandWindow.setHandler('nameGame2_' + index, this.commandNewGameSecond.bind(this, index));
            }
        }, this);
    };

    Scene_Title.prototype.fadeOutAll = function() {
        if (!this._noFadeout) {
            Scene_Base.prototype.fadeOutAll.apply(this, arguments);
        }
    };

    //=============================================================================
    // Scene_Load
    //  Moves to the Another Point when the load is successful.
    //=============================================================================
    var _Scene_Load_onLoadSuccess      = Scene_Load.prototype.onLoadSuccess;
    Scene_Load.prototype.onLoadSuccess = function() {
        _Scene_Load_onLoadSuccess.call(this);
        if (localExtraStageIndex >= 0) {
            var command = parameters.anotherDataList[localExtraStageIndex];
            var mapId = command.mapId;
            if (mapId > 0) {
                var x = command.mapX || 1;
                var y = command.mapY || 1;
                $gamePlayer.reserveTransfer(mapId, x, y);
            }
            $gameMap.abortInterpreter();
            DataManager.selectSavefileForNewGame();
            var switchId = command.switchId;
            if (switchId > 0) {
                $gameSwitches.setValue(switchId, true);
            }
        }
    };

    //=============================================================================
    // Window_TitleCommand
    //  Additional definition for the option of selecting Another New Game.
    //=============================================================================
    var _Window_TitleCommand_makeCommandList      = Window_TitleCommand.prototype.makeCommandList;
    Window_TitleCommand.prototype.makeCommandList = function() {
        _Window_TitleCommand_makeCommandList.call(this);
        parameters.anotherDataList.forEach(function(command, index) {
            if (ANGSettingManager.isVisible(index)) {
                this.makeAnotherNewGameCommand(command, index);
            }
        }, this);
        if (ANGSettingManager.newGameHidden) {
            this.eraseCommandNewGame();
        }
    };

    Window_TitleCommand.prototype.makeAnotherNewGameCommand = function(command, index) {
        this.addCommand(command.name, 'nameGame2_' + index, ANGSettingManager.isEnable(index));
        var addPosition = command.addPosition;
        if (addPosition > 0) {
            var anotherCommand = this._list.pop();
            this._list.splice(addPosition - 1, 0, anotherCommand);
        }
    };

    Window_TitleCommand.prototype.eraseCommandNewGame = function() {
        this._list = this._list.filter(function(command) {
            return command.symbol !== 'newGame';
        });
    };

    var _Window_TitleCommand_updatePlacement      = Window_TitleCommand.prototype.updatePlacement;
    Window_TitleCommand.prototype.updatePlacement = function() {
        _Window_TitleCommand_updatePlacement.call(this);
        var addSize = this._list.length - 3;
        if (addSize > 0) {
            this.y += addSize * this.itemHeight() / 2;
        }
    };

    //=============================================================================
    // ANGManager
    //  Defines the saving and loading of the Another New Game setting file.
    //=============================================================================
    function ANGSettingManager() {
        throw new Error('This is a static class');
    }

    ANGSettingManager._fileId = -1001;

    ANGSettingManager._visible       = [];
    ANGSettingManager._enable        = [];
    ANGSettingManager.newGameHidden = false;

    ANGSettingManager.make = function() {
        var info           = {};
        info.visible       = this._visible;
        info.enable        = this._enable;
        info.newGameHidden = this.newGameHidden;
        return info;
    };

    ANGSettingManager.isVisible = function(index) {
        if (this._visible[index] !== undefined && this._visible[index] !== null) {
            return this._visible[index];
        } else {
            return !parameters.anotherDataList[index].hidden;
        }
    };

    ANGSettingManager.setVisible = function(index, value) {
        this._visible[index] = value;
    };

    ANGSettingManager.isEnable = function(index) {
        if (this._enable[index] !== undefined && this._visible[index] !== null) {
            return this._enable[index];
        } else {
            return !parameters.anotherDataList[index].disable;
        }
    };

    ANGSettingManager.setEnable = function(index, value) {
        this._enable[index] = value;
    };

    ANGSettingManager.loadData = function() {
        var info           = this.load();
        this._visible      = info.visible || [];
        this._enable       = info.enable || [];
        this.newGameHidden = !!info.newGameHidden;
    };

    ANGSettingManager.load = function() {
        var json;
        try {
            json = StorageManager.load(this._fileId);
        } catch (e) {
            console.error(e);
            return [];
        }
        if (json) {
            return JSON.parse(json);
        } else {
            return [];
        }
    };

    ANGSettingManager.save = function() {
        var info = ANGSettingManager.make();
        StorageManager.save(this._fileId, JSON.stringify(info));
    };

    //=============================================================================
    // StorageManager
    //  Additional definition for the process of obtaining the path of the Another New Game setting file.
    //=============================================================================
    var _StorageManager_localFilePath = StorageManager.localFilePath;
    StorageManager.localFilePath      = function(savefileId) {
        if (savefileId === ANGSettingManager._fileId) {
            return this.localFileDirectoryPath() + 'AnotherNewGameMk2.rpgsave';
        } else {
            return _StorageManager_localFilePath.call(this, savefileId);
        }
    };

    var _StorageManager_webStorageKey = StorageManager.webStorageKey;
    StorageManager.webStorageKey      = function(savefileId) {
        if (savefileId === ANGSettingManager._fileId) {
            return 'RPG AnotherNewGame Mk2' + parameters.manageNumber;
        } else {
            return _StorageManager_webStorageKey.call(this, savefileId);
        }
    };
})();
