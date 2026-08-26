//=============================================================================
// PictureCallCommon.js
// ----------------------------------------------------------------------------
// (C)2015 Triacontane
// This plugin is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
// 1.14.5 2023/02/20 Fixed an issue where mouseover detection was erroneously functioning even when picture attachment was not set
// 1.14.4 2021/08/22 Fixed an issue where the "Execute as Parallel Processing" parameter was not being applied to the battle screen
// 1.14.3 2021/05/01 Changed the setting values when detaching the attachment
// 1.14.2 2020/06/05 Added pagedown and pageup to the help key bindings
// 1.14.1 2020/05/16 Corrected confusing descriptions in the command section of the help
// 1.14.0 2020/05/13 Added a setting to enable "Touch Operation Suppression" only when the specified switch is ON
// 1.13.1 2020/05/06 Fixed an issue where the coordinate acquisition calculation was incorrect when executing map zoom
// 1.13.0 2019/12/22 Added a setting to run picture common as parallel processing
// 1.12.2 2019/03/31 Changed the specification so that keys specified additionally in the key binding will respond even if the button name is in lowercase
// 1.12.1 2019/03/19 When moving routes were set from Picture Commons in community edition core scripts 1.3 or later, an error was fixed.
// 1.12.0 2018/11/02 Added a switch to disable all picture touches.
// 1.11.0 2018/08/10 Fixed an issue where the transparency setting was not correctly applied to petting functionality.
//                   Added a function to change the transparency setting from plugin commands for petting functionality.
// 1.10.8 2018/06/16 Fixed an issue where boolean parameters were not obtained properly in some cases.
// 1.10.7 2018/06/01 Fixed an issue where the "Always Common Execution During Battle" feature could not be used when battles are processed by the "Battle Processing" event.
// 1.10.6 2018/04/12 Slightly corrected the description in the help.
// 1.10.5 2017/12/17 Changed the specification so that button types that execute common events become invalid during event execution.
// 1.10.4 2017/11/01 Changed the specification so that the event is not called if the target picture is not displayed at the moment Picture Commons is called.
// 1.10.3 2017/10/28 Fixed an issue where the event is executed after the battle screen is displayed when a picture touch event call is in progress and a battle is entered.
// 1.10.2 2017/10/21 A problem where unexpected mouseover events occur in the battle screen effects has been fixed.
// 1.10.1 2017/05/27 Modified the window frame click to respond as a picture click for the animated text string picture plugin.
// 1.9.3 2017/05/27 Refactored the potentially conflicting description (property addition to the Object class) by liply.
// 1.9.2 2017/03/16 Fixed a problem where common events did not function correctly during battle in version 1.9.0.
// 1.9.1 2017/03/16 Changed the specification so that pictures with transparency set to 0 will not respond at all when considering transparency.
// 1.9.0 2017/03/13 Added a feature to always execute picture click events during battle.
// 1.8.2 2017/02/14 Fixed a problem where the function to store values in variables during picture clicks was disabled due to the corrections in version 1.8.0.
// 1.8.1 2017/02/07 Removed platform-dependent descriptions.
// 1.8.0 2017/02/03 Added a feature to bind picture clicks to any button.
// 1.7.0 2017/02/02 It is now possible to accurately click on pictures even during map zoom and shake.
//                  The feature to determine with a script whether the mouse pointer is within the picture has been added.
// 1.6.0 2016/12/29 The feature has been modified so that map touch is disabled when an event occurs from picture click.
// 1.5.1 2016/11/20 Unnecessary code mixed in 1.5.0 has been removed.
// 1.5.0 2016/11/19 A feature to turn a switch ON instead of using a common event when clicking a picture has been added.
// 1.4.0 2016/08/20 The ability to set whether to consider the transparent color for each picture has been added.
//                  The error that occurs when loading save data without applying the plugin has been fixed.
// 1.3.5 2016/04/20 The priority order of pictures has been restored after refactoring.
// 1.3.4 2016/04/08 A problem where mouse over and mouse out functions incorrectly when pictures are adjacent has been fixed.
// 1.3.3 2016/03/19 A parameter to suppress further touch processing when a trigger condition is met has been added.
// 1.3.2 2016/02/28 The processing load has been slightly reduced.
// 1.3.1 2016/02/21 Add movement while holding the mouse button for the trigger
// 1.3.0 2016/01/24 Add the ability to swipe the picture
//                  Add mouse move to the trigger
//                  Correct positioning when the picture is rotating
// 1.2.1 2016/01/21 Change the上限 of called common events from 100 to 1000 (maximum value on the DB)
//                  Countermeasure (YEP_MessageCore.js)
// 1.2.0 2016/01/14 Expand the triggers to 10 types including wheel click and double click
// 1.1.3 2016/01/02 Change the specification to set a 1-second interval for events triggered by long press
// 1.1.2 2015/12/20 Correct the phenomenon where an error occurs when hovering over a picture after it has been deleted
// 1.1.1 2015/12/10 Correct the phenomenon where an error occurs when the mouse is hovered over a picture after it has been deleted
// 1.1.0 2015/11/23 Add a function to specify the picture number of the target that called the common event
//                  Add a function to consider the transparent color setting
//                  Add 'Right-click' and 'Long-press' as triggers
// 1.0.0 2015/11/14 First edition
// ----------------------------------------------------------------------------
// [Blog]   : https://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:ja
 * @plugindesc [移動]　ピクチャのボタン化プラグイン
 * @author トリアコンタン
 *
 * @param 透明色を考慮
 * @desc クリックされた箇所が透明色だった場合は、クリックを無効にする。
 * @default true
 * @type boolean
 *
 * @param ピクチャ番号の変数番号
 * @desc ピクチャクリック時にピクチャ番号を格納するゲーム変数の番号。
 * @default 0
 * @type variable
 *
 * @param ポインタX座標の変数番号
 * @desc マウスカーソルもしくはタッチした位置のX座標を常に格納するゲーム変数の番号
 * @default 0
 * @type variable
 *
 * @param ポインタY座標の変数番号
 * @desc マウスカーソルもしくはタッチした位置のY座標を常に格納するゲーム変数の番号
 * @default 0
 * @type variable
 *
 * @param タッチ操作抑制
 * @desc トリガー条件を満たした際にタッチ情報をクリアします。(ON/OFF)
 * Enable this if other touch operations interfere with its functionality.
 * @default false
 * @type boolean
 *
 * @param タッチ操作抑制スイッチ
 * @desc 指定した場合、対象スイッチがONのときのみ「タッチ操作抑制」が有効になります。
 * @default 0
 * @type switch
 *
 * @param 戦闘中常にコモン実行
 * @desc 戦闘中にピクチャをクリックしたとき、常にコモンイベントを実行します。(ON/OFF)
 * @default false
 * @type boolean
 *
 * @param 並列処理として実行
 * @desc ピクチャクリックによるコモンイベント実行を並列処理扱いで実行します。
 * @default false
 * @type boolean
 *
 * @param 無効スイッチ
 * @desc 指定した番号のスイッチがONになっている場合、すべてのピクチャタッチが無効になります。
 * @default 0
 * @type switch
 *
 * @help ピクチャをクリックすると、指定したコモンイベントが
 * Provides plugin commands to turn on called or arbitrary switches when the plugin is invoked.
 * With this plugin, anyone without knowledge of JavaScript
 * can easily create games centered around clicks and touches.
 *
 * While executable in battle, due to the MZ system specifications, events can only run at limited times.
 * Enabling the parameter 'Always Execute Common Events in Battle' will
 * It will always execute events, but there are limitations where some event commands may not function correctly.
 * Note that there are constraints where some event commands may not function correctly.
 *
 * Warning!
 * Once related pictures and common events are linked, they remain effective even if the picture is deleted.
 * If the picture does not exist, clicking anywhere will not respond,
 * but if the same numbered picture is displayed again, it will start responding.
 *
 * Plugin command details
 *  Execute via the event command "Plugin Command".
 * (Arguments are separated by a space)
 *
 * Picture buttonization or
 *  P_CALL_CE [ピクチャ番号] [コモンイベントID] [トリガー] [透明色を考慮]
 * This associates a common event to be called when the trigger condition is met within the picture's area.
 *  　　The trigger is as follows: (It becomes 1 if omitted)
 *      1  : When clicked
 *      2  : When right-clicked
 *      3  : When long-pressed
 *      4  : When the mouse is hovered over the picture
 *      5  : When the mouse is released from the picture
 *      6  : When the click is released (released)
 *      7  : When clicked (considering the repetition during long press)
 *      8  : While clicking (considering the repetition during long press)
 *      9  : When wheel-clicked (only effective on PC)
 *      10 : Double-clicked case
 *      11 : Mouse moved within the picture
 *      12 : Mouse pressed and moved within the picture
 *
 *      A parameter to specify whether to consider the transparent color (ON/OFF) allows setting whether to consider the transparent color on a per-picture basis.
 *      If nothing is set, the plugin parameter settings will be applied. (Previous behavior)
 *
 *  Example: P_CALL_CE 1 3 7 ON
 *  　: Picture buttonization \v[1] \v[2] \v[3] OFF
 *
 *  Picture switch activation or
 *  P_CALL_SWITCH [ピクチャ番号] [スイッチID] [トリガー] [透明色を考慮]
 *  　If the trigger condition is met within the picture area, it will turn on any switch you specify.
 *  　　The setup for triggers is the same as for buttonizing pictures.
 *
 *  Picture key binding or
 *  P_CALL_KEY_BIND [ピクチャ番号] [ボタン名称] [トリガー] [透明色を考慮]
 *  　　When the trigger conditions are met within the picture's area, it will be considered as pressing any button.
 *  　　The setting for button names is as follows (based on Windows).
 *  ok       : Enter,Z
 *  shift    : Shift
 *  control  : Ctrl,Alt
 *  escape   : Esc,X
 *  left     : ←
 *  up       : ↑
 *  right    : →
 *  down     : ↓
 *  pageup   : PageUp
 *  pagedown : PageDown
 *
 *  Picture buttonization removal or
 *  P_CALL_CE_REMOVE [ピクチャ番号]
 *      The association between the picture and common event or switch is removed.
 *      All triggers are targets for deletion.
 *
 *  Example: P_CALL_CE_REMOVE 1
 *  　：Button removal for picture \v[1]
 *
 *  Picture stroke setting or
 *  P_STROKE [ピクチャ番号] [変数番号] [透明色を考慮]
 *  　　When moving the mouse or touch on the specified picture,
 *  　　the value will be added to the specified variable at a speed-dependent rate.
 *  　　This setting remains effective even when the picture is replaced or temporarily hidden.
 *  　　It will accumulate to about 1000 in roughly 10 seconds.
 *
 *  Example: P_STROKE 1 2 ON
 *  　：Picture stroke setting \v[1] \v[2] OFF
 *
 *  Remove picture stroke setting or
 *  P_STROKE_REMOVE [ピクチャ番号]
 *  　　Removes the stroke setting for the specified picture.
 *
 *  Example: P_STROKE_REMOVE 1
 *  　：Removes the stroke for the picture \v[1]
 *
 *  Pointerize the picture or
 *  P_POINTER [ピクチャ番号]
 *  　　The specified picture will automatically follow touch coordinates.
 *  　　It will automatically become invisible if not touched.
 *
 *  Example: P_POINTER 1
 *  　：Pointerizes the picture \v[1]
 *
 *  Unpin the picture pointer or
 *  P_POINTER_REMOVE [ピクチャ番号]
 *  　　Removes the pointerization of the specified picture.
 *
 *  Example: P_POINTER_REMOVE 1
 *  　：Unpin the picture pointer \v[1]
 *
 *  ・Script (For Advanced Users)
 *  $gameScreen.isPointerInnerPicture([ID]);
 *
 *  Returns true if the mouse pointer or touch coordinate exists within the picture specified by [ID].
 *  This script is effective even without using [P_CALL_CE].
 *
 *  Example: $gameScreen.isPointerInnerPicture(5);
 *
 * Terms of Use:
 *  Modification and redistribution without the author's consent are allowed,
 *  and there are no restrictions on usage (commercial, 18+ use, etc.).
 *  This plugin is now yours.
 */
/*:
 * @plugindesc Clickable picture plugin
 * @author triacontane
 *
 * @param TransparentConsideration
 * @desc if click position is transparent, click is disabled.
 * @default true
 * @type boolean
 *
 * @param GameVariablePictureNum
 * @desc Game variable number that stores the picture number when common event called.
 * @default 0
 * @type variable
 *
 * @param GameVariableTouchX
 * @desc Game variable number that stores touch x position
 * @default 0
 * @type variable
 *
 * @param GameVariableTouchY
 * @desc Game variable number that stores touch y position
 * @default 0
 * @type variable
 *
 * @param SuppressTouch
 * @desc Suppress touch event for others(ON/OFF)
 * @default false
 * @type boolean
 *
 * @param SuppressTouchSwitch
 * @desc If this is specified, the "SuppressTouch" is enabled only when the target switch is on.
 * @default 0
 * @type switch
 *
 * @param AlwaysCommonInBattle
 * @desc Always execute common event in battle(ON/OFF)
 * @default false
 * @type boolean
 *
 * @param AsParallelCommon
 * @desc ピクチャクリックによるコモンイベント実行を並列処理扱いで実行します。
 * @default false
 * @type boolean
 *
 * @param InvalidSwitchId
 * @desc 指定した番号のスイッチがONになっている場合、すべてのピクチャタッチが無効になります。
 * @default 0
 * @type switch
 *
 * @help When clicked picture, call common event.
 *
 * Plugin Command
 *
 *  P_CALL_CE [Picture number] [Common event ID] [Trigger] [TransparentConsideration]:
 *      When picture was clicked, assign common event id.
 *  　　Trigger are As below(if omit, It is specified to 1)
 *      1  : Left click
 *      2  : Right click
 *      3  : Long click
 *      4  : Mouse over
 *      5  : Mouse out
 *      6  : Mouse release
 *      7  : Mouse repeat click
 *      8  : Mouse press
 *      9  : Wheel click
 *      10 : Double click
 *      11 : Mouse move
 *      12 : Mouse move and press
 *
 *  P_CALL_CE_REMOVE [Picture number] :
 *      break relation from picture to common event.
 *
 *  - Script
 *  $gameScreen.isPointerInnerPicture([ID]);
 *
 *  If mouse pointer inner the picture, return true.
 *
 *  ex：$gameScreen.isPointerInnerPicture(5);
 *
 *  This plugin is released under the MIT License.
 */
(function() {
    'use strict';
    var pluginName = 'PictureCallCommon';

    var getParamOther = function(paramNames) {
        if (!Array.isArray(paramNames)) paramNames = [paramNames];
        for (var i = 0; i < paramNames.length; i++) {
            var name = PluginManager.parameters(pluginName)[paramNames[i]];
            if (name) return name;
        }
        return null;
    };

    var getParamBoolean = function(paramNames) {
        var value = getParamOther(paramNames);
        return (value || '').toUpperCase() === 'ON' || (value || '').toUpperCase() === 'TRUE';
    };

    var getParamNumber = function(paramNames, min, max) {
        var value = getParamOther(paramNames);
        if (arguments.length < 2) min = -Infinity;
        if (arguments.length < 3) max = Infinity;
        return (parseInt(value, 10) || 0).clamp(min, max);
    };

    var getCommandName = function(command) {
        return (command || '').toUpperCase();
    };

    var getArgNumber = function(arg, min, max) {
        if (arguments.length < 2) min = -Infinity;
        if (arguments.length < 3) max = Infinity;
        return (parseInt(convertEscapeCharacters(arg), 10) || 0).clamp(min, max);
    };

    var getArgBoolean = function(arg) {
        return (arg || '').toUpperCase() === 'ON';
    };

    var convertEscapeCharacters = function(text) {
        if (text == null) text = '';
        var window = SceneManager._scene._windowLayer.children[0];
        return window ? window.convertEscapeCharacters(text) : text;
    };

    var iterate = function(that, handler) {
        Object.keys(that).forEach(function(key, index) {
            handler.call(that, key, that[key], index);
        });
    };

    //=============================================================================
    // Parameter retrieval and validation
    //=============================================================================
    var paramGameVariableTouchX       = getParamNumber(['GameVariableTouchX', 'Pointer X coordinate variable number'], 0);
    var paramGameVariableTouchY       = getParamNumber(['GameVariableTouchY', 'Pointer Y coordinate variable number'], 0);
    var paramGameVariablePictNum      = getParamNumber(['GameVariablePictureNum', 'Picture number variable number'], 0);
    var paramTransparentConsideration = getParamBoolean(['TransparentConsideration', 'Consider Transparent Color']);
    var paramSuppressTouch            = getParamBoolean(['SuppressTouch', 'Touch operation suppression']);
    var paramSuppressTouchSwitch      = getParamNumber(['SuppressTouchSwitch', 'Touch operation suppression switch']);
    var paramAlwaysCommonInBattle     = getParamBoolean(['AlwaysCommonInBattle', 'Always execute common during battle']);
    var paramInvalidSwitchId          = getParamNumber(['InvalidSwitchId', 'Invalid switch'], 0);
    var paramAsParallelCommon         = getParamBoolean(['AsParallelCommon', 'Execute as parallel process']);

    //=============================================================================
    // Game_Interpreter
    // Additional definitions for plugin commands such as [P_CALL_CE].
    //=============================================================================
    var _Game_Interpreter_pluginCommand      = Game_Interpreter.prototype.pluginCommand;
    Game_Interpreter.prototype.pluginCommand = function(command, args) {
        _Game_Interpreter_pluginCommand.apply(this, arguments);
        var pictureId, touchParam, trigger, variableNum, transparent;
        switch (getCommandName(command)) {
            case 'P_CALL_CE' :
            case 'Picture buttonization':
                pictureId   = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                touchParam  = getArgNumber(args[1], 1, $dataCommonEvents.length - 1);
                trigger     = getArgNumber(args[2], 1);
                transparent = (args.length > 3 ? getArgBoolean(args[3]) : null);
                $gameScreen.setPictureCallCommon(pictureId, touchParam, trigger, transparent);
                break;
            case 'P_CALL_SWITCH' :
            case 'Picture switchization':
                pictureId   = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                touchParam  = getArgNumber(args[1], 1);
                trigger     = getArgNumber(args[2], 1);
                transparent = (args.length > 3 ? getArgBoolean(args[3]) : null);
                $gameScreen.setPictureCallCommon(pictureId, touchParam * -1, trigger, transparent);
                break;
            case 'P_CALL_KEY_BIND' :
            case 'Picture keybinding':
                pictureId   = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                touchParam  = convertEscapeCharacters(args[1]);
                trigger     = getArgNumber(args[2], 1);
                transparent = (args.length > 3 ? getArgBoolean(args[3]) : null);
                $gameScreen.setPictureCallCommon(pictureId, touchParam, trigger, transparent);
                break;
            case 'P_CALL_CE_REMOVE' :
            case 'Remove picture buttonization':
                pictureId = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                $gameScreen.setPictureRemoveCommon(pictureId);
                break;
            case 'P_STROKE' :
            case 'Picture petting setting':
                pictureId   = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                variableNum = getArgNumber(args[1], 1, $dataSystem.variables.length - 1);
                transparent = (args.length > 2 ? getArgBoolean(args[2]) : null);
                $gameScreen.setPictureStroke(pictureId, variableNum, transparent);
                break;
            case 'P_STROKE_REMOVE' :
            case 'Remove picture petting':
                pictureId = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                $gameScreen.removePictureStroke(pictureId);
                break;
            case 'P_POINTER' :
            case 'Picture pointerization':
                pictureId = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                $gameScreen.setPicturePointer(pictureId);
                break;
            case 'P_POINTER_REMOVE' :
            case 'Remove picture pointerization':
                pictureId = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                $gameScreen.removePicturePointer(pictureId);
                break;
        }
    };

    var _Game_Interpreter_terminate      = Game_Interpreter.prototype.terminate;
    Game_Interpreter.prototype.terminate = function() {
        _Game_Interpreter_terminate.apply(this, arguments);
        this._setupFromPicture = false;
    };

    Game_Interpreter.prototype.setupFromPicture = function(eventList, commonId) {
        this.setup(eventList, null);
        if (this.setEventInfo) {
            this.setEventInfo({ eventType: 'common_event', commonEventId: commonId });
        }
        this._setupFromPicture = true;
    };

    Game_Interpreter.prototype.isSetupFromPicture = function() {
        return this._setupFromPicture;
    };

    //=============================================================================
    // Game_Temp
    // Additional definitions for fields of planned common event IDs to be called.
    //=============================================================================
    var _Game_Temp_initialize      = Game_Temp.prototype.initialize;
    Game_Temp.prototype.initialize = function() {
        _Game_Temp_initialize.call(this);
        this.clearPictureCallInfo();
    };

    Game_Temp.prototype.clearPictureCallInfo = function() {
        this._pictureCommonId = 0;
        this._touchPictureId  = 0;
    };

    Game_Temp.prototype.setPictureCallInfo = function(pictureCommonId) {
        this._pictureCommonId = pictureCommonId;
    };

    Game_Temp.prototype.pictureCommonId = function() {
        if (!$gameScreen.picture(this._touchPictureId)) {
            this.clearPictureCallInfo();
        }
        return this._pictureCommonId;
    };

    Game_Temp.prototype.onTouchPicture = function(param, pictureId) {
        this._touchPictureParam = param;
        if (this.isTouchPictureSetSwitch()) {
            $gameSwitches.setValue(param * -1, true);
        }
        if (this.isTouchPictureCallCommon()) {
            if (!paramAsParallelCommon && $gameMap.isEventRunning() && !$gameParty.inBattle()) {
                this._touchPictureParam = null;
                return;
            }
            this.setPictureCallInfo(param);
        }
        if (this.isTouchPictureButtonTrigger()) {
            Input.bindKeyState(param);
        }
        if (paramGameVariablePictNum > 0) {
            $gameVariables.setValue(paramGameVariablePictNum, pictureId);
        }
        this._touchPictureId = pictureId;
    };

    Game_Temp.prototype.isTouchPictureButtonTrigger = function() {
        return isNaN(this._touchPictureParam);
    };

    Game_Temp.prototype.isTouchPictureSetSwitch = function() {
        return !isNaN(this._touchPictureParam) && this._touchPictureParam < 0;
    };

    Game_Temp.prototype.isTouchPictureCallCommon = function() {
        return !isNaN(this._touchPictureParam) && this._touchPictureParam > 0;
    };

    //=============================================================================
    // Game_System
    //  Initializes picture-related members when loading.
    //=============================================================================
    var _Game_System_onAfterLoad      = Game_System.prototype.onAfterLoad;
    Game_System.prototype.onAfterLoad = function() {
        _Game_System_onAfterLoad.apply(this, arguments);
        $gameScreen.initPictureArray();
    };

    //=============================================================================
    // Game_Map
    //  Adds a definition for the common event call process when a picture is touched.
    //=============================================================================
    var _Game_Map_setupStartingEvent      = Game_Map.prototype.setupStartingEvent;
    Game_Map.prototype.setupStartingEvent = function() {
        var result = _Game_Map_setupStartingEvent.call(this);
        return result || this.setupPictureCommonEvent();
    };

    var _Game_Map_updateInterpreter = Game_Map.prototype.updateInterpreter;
    Game_Map.prototype.updateInterpreter = function() {
        _Game_Map_updateInterpreter.apply(this, arguments);
        this.setupPictureParallelCommonEvent();
    };

    Game_Map.prototype.setupPictureParallelCommonEvent = function() {
        if (!paramAsParallelCommon) {
            return;
        }
        var commonId = $gameTemp.pictureCommonId();
        var event    = $dataCommonEvents[commonId];
        if (event) {
            if (!this._pictureCommonEvents) {
                this._pictureCommonEvents = [];
            }
            var interpreter = new Game_Interpreter();
            interpreter.setupFromPicture(event.list, commonId);
            this._pictureCommonEvents.push(interpreter);
            $gameTemp.clearPictureCallInfo();
        }
    };

    Game_Map.prototype.setupPictureCommonEvent = function() {
        if (paramAsParallelCommon) {
            return false;
        }
        var commonId = $gameTemp.pictureCommonId();
        var event    = $dataCommonEvents[commonId];
        var result   = false;
        if (!this.isEventRunning() && event) {
            this._interpreter.setupFromPicture(event.list, commonId);
            result = true;
        }
        $gameTemp.clearPictureCallInfo();
        return result;
    };

    var _Game_Map_updateEvents = Game_Map.prototype.updateEvents;
    Game_Map.prototype.updateEvents = function() {
        _Game_Map_updateEvents.apply(this, arguments);
        if (this._pictureCommonEvents && this._pictureCommonEvents.length > 0) {
            this.updatePictureCommonEvents();
        }
    };

    Game_Map.prototype.updatePictureCommonEvents = function() {
        this._pictureCommonEvents.forEach(function(event) {
            event.update();
        });
        this._pictureCommonEvents = this._pictureCommonEvents.filter(function(event) {
            return event.isRunning();
        })
    };

    //=============================================================================
    // Game_Troop
    //  Adds a definition for the common event call process when a picture is touched.
    //=============================================================================
    Game_Troop.prototype.setupPictureCommonEvent = Game_Map.prototype.setupPictureCommonEvent;
    Game_Troop.prototype.setupPictureParallelCommonEvent = Game_Map.prototype.setupPictureParallelCommonEvent;
    Game_Troop.prototype.updatePictureCommonEvents = Game_Map.prototype.updatePictureCommonEvents;

    Game_Troop.prototype.updateAllPictureCommonEvent = function() {
        this.setupPictureCommonEvent();
        this.setupPictureParallelCommonEvent();
        if (this._pictureCommonEvents && this._pictureCommonEvents.length > 0) {
            this.updatePictureCommonEvents();
        }
    };

    Game_Troop.prototype.isExistPictureCommon = function() {
        return this._interpreter.isSetupFromPicture();
    };

    //=============================================================================
    // Game_Screen
    //  Adds a definition for an ID array used to call common events corresponding to the picture.
    //=============================================================================
    var _Game_Screen_initialize      = Game_Screen.prototype.initialize;
    Game_Screen.prototype.initialize = function() {
        _Game_Screen_initialize.apply(this, arguments);
        this.initPictureArray();
    };

    Game_Screen.prototype.initPictureArray = function() {
        this._pictureCidArray         = this._pictureCidArray || [];
        this._pictureSidArray         = this._pictureSidArray || [];
        this._picturePidArray         = this._picturePidArray || [];
        this._pictureTransparentArray = this._pictureTransparentArray || [];
    };

    var _Game_Screen_update      = Game_Screen.prototype.update;
    Game_Screen.prototype.update = function() {
        _Game_Screen_update.apply(this, arguments);
        this.updatePointer();
    };

    Game_Screen.prototype.updatePointer = function() {
        if (paramGameVariableTouchX)
            $gameVariables._data[paramGameVariableTouchX] = TouchInput.x;
        if (paramGameVariableTouchY)
            $gameVariables._data[paramGameVariableTouchY] = TouchInput.y;
    };

    Game_Screen.prototype.setPictureCallCommon = function(pictureId, touchParameter, trigger, transparent) {
        var realPictureId = this.realPictureId(pictureId);
        if (this._pictureCidArray[realPictureId] == null) this._pictureCidArray[realPictureId] = [];
        this._pictureCidArray[realPictureId][trigger] = touchParameter;
        this._pictureTransparentArray[realPictureId]  = transparent;
    };

    Game_Screen.prototype.setPictureRemoveCommon = function(pictureId) {
        this._pictureCidArray[this.realPictureId(pictureId)] = null;
    };

    Game_Screen.prototype.setPictureStroke = function(pictureId, variableNum, transparent) {
        var realPictureId = this.realPictureId(pictureId);
        this._pictureSidArray[realPictureId] = variableNum;
        this._pictureTransparentArray[realPictureId] = transparent;
    };

    Game_Screen.prototype.removePictureStroke = function(pictureId) {
        this._pictureSidArray[this.realPictureId(pictureId)] = null;
    };

    Game_Screen.prototype.setPicturePointer = function(pictureId) {
        this._picturePidArray[this.realPictureId(pictureId)] = true;
    };

    Game_Screen.prototype.removePicturePointer = function(pictureId) {
        this._picturePidArray[this.realPictureId(pictureId)] = null;
    };

    Game_Screen.prototype.getPictureCid = function(pictureId) {
        return this._pictureCidArray[this.realPictureId(pictureId)];
    };

    Game_Screen.prototype.getPictureSid = function(pictureId) {
        return this._pictureSidArray[this.realPictureId(pictureId)];
    };

    Game_Screen.prototype.getPicturePid = function(pictureId) {
        return this._picturePidArray[this.realPictureId(pictureId)];
    };

    Game_Screen.prototype.getPictureTransparent = function(pictureId) {
        return this._pictureTransparentArray[this.realPictureId(pictureId)];
    };

    Game_Screen.prototype.disConvertPositionX = function(x) {
        var unshiftX = x - this.zoomX() * (1 - this.zoomScale());
        return Math.round(unshiftX / this.zoomScale());
    };

    Game_Screen.prototype.disConvertPositionY = function(y) {
        var unshiftY = y - this.zoomY() * (1 - this.zoomScale());
        return Math.round(unshiftY / this.zoomScale());
    };

    Game_Screen.prototype.isPointerInnerPicture = function(pictureId) {
        var picture = SceneManager.getPictureSprite(pictureId);
        return picture ? picture.isIncludePointer() : false;
    };

    //=============================================================================
    // SceneManager
    //  Gets the picture sprite.
    //=============================================================================
    SceneManager.getPictureSprite = function(pictureId) {
        return this._scene.getPictureSprite(pictureId);
    };

    //=============================================================================
    // BattleManager
    //  Ensures that the picture common event can always be executed.
    //=============================================================================
    BattleManager.updatePictureCommon = function() {
        if ($gameTroop.isExistPictureCommon() && paramAlwaysCommonInBattle) {
            this.updateEventMain();
            return true;
        }
        return false;
    };

    //=============================================================================
    // Scene_Base
    //  Adds a definition for a loop process for the picture.
    //=============================================================================
    Scene_Base.prototype.updateTouchPictures = function() {
        if (paramInvalidSwitchId && $gameSwitches.value(paramInvalidSwitchId)) {
            return;
        }
        this._spriteset.iteratePictures(function(picture) {
            if (typeof picture.callTouch === 'function') picture.callTouch();
            return $gameTemp.pictureCommonId() === 0;
        });
    };

    Scene_Base.prototype.getPictureSprite = function(pictureId) {
        var result = null;
        this._spriteset.iteratePictures(function(picture) {
            if (picture.isIdEquals(pictureId)) {
                result = picture;
                return false;
            }
            return true;
        });
        return result;
    };

    //=============================================================================
    // Scene_Map
    //  Adds a definition for reserving a common event call from the picture's touch state.
    //=============================================================================
    var _Scene_Map_update      = Scene_Map.prototype.update;
    Scene_Map.prototype.update = function() {
        this.updateTouchPictures();
        _Scene_Map_update.apply(this, arguments);
    };

    var _Scene_Map_processMapTouch      = Scene_Map.prototype.processMapTouch;
    Scene_Map.prototype.processMapTouch = function() {
        _Scene_Map_processMapTouch.apply(this, arguments);
        if ($gameTemp.isDestinationValid() && $gameTemp.pictureCommonId() > 0) {
            $gameTemp.clearDestination();
        }
    };

    var _Scene_Map_terminate      = Scene_Map.prototype.terminate;
    Scene_Map.prototype.terminate = function() {
        _Scene_Map_terminate.apply(this, arguments);
        $gameTemp.clearPictureCallInfo();
    };

    //=============================================================================
    // Scene_Battle
    //  Adds a definition for reserving a common event call from the picture's touch state.
    //=============================================================================
    var _Scene_Battle_update      = Scene_Battle.prototype.update;
    Scene_Battle.prototype.update = function() {
        this.updateTouchPictures();
        $gameTroop.updateAllPictureCommonEvent();
        _Scene_Battle_update.apply(this, arguments);
    };

    var _Scene_Battle_updateBattleProcess      = Scene_Battle.prototype.updateBattleProcess;
    Scene_Battle.prototype.updateBattleProcess = function() {
        var result = BattleManager.updatePictureCommon();
        if (result) return;
        _Scene_Battle_updateBattleProcess.apply(this, arguments);
    };

    var _Scene_Battle_terminate      = Scene_Battle.prototype.terminate;
    Scene_Battle.prototype.terminate = function() {
        _Scene_Battle_terminate.apply(this, arguments);
        $gameTemp.clearPictureCallInfo();
    };

    //=============================================================================
    // Spriteset_Base
    //  Adds a definition for an iterator for the picture.
    //=============================================================================
    Spriteset_Base.prototype.iteratePictures = function(callBackFund) {
        var containerChildren = this._pictureContainer.children;
        if (!Array.isArray(containerChildren)) {
            iterate(this._pictureContainer, function(property) {
                if (this._pictureContainer[property].hasOwnProperty('children')) {
                    containerChildren = this._pictureContainer[property].children;
                    this._iteratePicturesSub(containerChildren, callBackFund);
                }
            }.bind(this));
        } else {
            this._iteratePicturesSub(containerChildren, callBackFund);
        }
    };

    Spriteset_Base.prototype._iteratePicturesSub = function(containerChildren, callBackFund) {
        for (var i = containerChildren.length - 1; i >= 0; i--) {
            if (!callBackFund(containerChildren[i])) {
                break;
            }
        }
    };

    //=============================================================================
    // Sprite_Picture
    //  Adds a definition for reserving a common event call from the picture's touch state.
    //=============================================================================
    var _Sprite_Picture_initialize      = Sprite_Picture.prototype.initialize;
    Sprite_Picture.prototype.initialize = function(pictureId) {
        _Sprite_Picture_initialize.call(this, pictureId);
        this._triggerHandler     = [];
        this._triggerHandler[1]  = this.isTriggered;
        this._triggerHandler[2]  = this.isCancelled;
        this._triggerHandler[3]  = this.isLongPressed;
        this._triggerHandler[4]  = this.isOnFocus;
        this._triggerHandler[5]  = this.isOutFocus;
        this._triggerHandler[6]  = this.isReleased;
        this._triggerHandler[7]  = this.isRepeated;
        this._triggerHandler[8]  = this.isPressed;
        this._triggerHandler[9]  = this.isWheelTriggered;
        this._triggerHandler[10] = this.isDoubleTriggered;
        this._triggerHandler[11] = this.isMoved;
        this._triggerHandler[12] = this.isMovedAndPressed;
        this._onMouse            = false;
        this._outMouse           = false;
        this._wasOnMouse         = false;
    };

    var _Sprite_update              = Sprite_Picture.prototype.update;
    Sprite_Picture.prototype.update = function() {
        _Sprite_update.apply(this, arguments);
        this.updateTouch();
    };

    Sprite_Picture.prototype.updateTouch = function() {
        this.updateMouseMove();
        this.updateStroke();
        this.updatePointer();
    };

    Sprite_Picture.prototype.updateMouseMove = function() {
        var commandIds = $gameScreen.getPictureCid(this._pictureId);
        if (!commandIds) {
            this._outMouse   = false;
            this._wasOnMouse = false;
            return;
        }
        if (this.isIncludePointer()) {
            if (!this._wasOnMouse) {
                this._onMouse    = true;
                this._wasOnMouse = true;
            }
        } else if (this._wasOnMouse) {
            this._outMouse   = true;
            this._wasOnMouse = false;
        }
    };

    Sprite_Picture.prototype.isIncludePointer = function() {
        return this.isTouchable() && this.isTouchPosInRect() && !this.isTransparent();
    };

    Sprite_Picture.prototype.updateStroke = function() {
        var strokeNum = $gameScreen.getPictureSid(this._pictureId);
        if (strokeNum > 0 && TouchInput.isPressed() && this.isIncludePointer()) {
            var value = $gameVariables.value(strokeNum);
            $gameVariables.setValue(strokeNum, value + TouchInput.pressedDistance);
        }
    };

    Sprite_Picture.prototype.updatePointer = function() {
        var strokeNum = $gameScreen.getPicturePid(this._pictureId);
        if (strokeNum > 0) {
            this.opacity  = TouchInput.isPressed() ? 255 : 0;
            this.x        = TouchInput.x;
            this.y        = TouchInput.y;
            this.anchor.x = 0.5;
            this.anchor.y = 0.5;
        }
    };

    Sprite_Picture.prototype.callTouch = function() {
        var commandIds = $gameScreen.getPictureCid(this._pictureId);
        if (!commandIds || SceneManager.isNextScene(Scene_Battle)) {
            return;
        }
        for (var i = 0, n = this._triggerHandler.length; i < n; i++) {
            var handler = this._triggerHandler[i];
            if (handler && commandIds[i] && handler.call(this) && (this.triggerIsFocus(i) || !this.isTransparent())) {
                this.fireTouchEvent(commandIds, i);
            }
        }
    };

    Sprite_Picture.prototype.fireTouchEvent = function(commandIds, i) {
        if (this.isTouchSuppress()) {
            TouchInput.suppressEvents();
        }
        if (this.triggerIsLongPressed(i)) TouchInput._pressedTime = -60;
        if (this.triggerIsOnFocus(i)) this._onMouse = false;
        if (this.triggerIsOutFocus(i)) this._outMouse = false;
        $gameTemp.onTouchPicture(commandIds[i], this._pictureId);
    };

    Sprite_Picture.prototype.isTouchSuppress = function() {
        return paramSuppressTouchSwitch > 0 ? $gameSwitches.value(paramSuppressTouchSwitch) : paramSuppressTouch;
    };

    Sprite_Picture.prototype.triggerIsLongPressed = function(triggerId) {
        return triggerId === 3;
    };

    Sprite_Picture.prototype.triggerIsOnFocus = function(triggerId) {
        return triggerId === 4;
    };

    Sprite_Picture.prototype.triggerIsOutFocus = function(triggerId) {
        return triggerId === 5;
    };

    Sprite_Picture.prototype.triggerIsFocus = function(triggerId) {
        return this.triggerIsOnFocus(triggerId) || this.triggerIsOutFocus(triggerId);
    };

    Sprite_Picture.prototype.isTransparent = function() {
        if (this.isTouchPosInFrameWindow()) return false;
        if (!this.isValidTransparent()) return false;
        if (this.opacity === 0) return true;
        var dx  = this.getTouchScreenX() - this.x;
        var dy  = this.getTouchScreenY() - this.y;
        var sin = Math.sin(-this.rotation);
        var cos = Math.cos(-this.rotation);
        var bx  = Math.floor(dx * cos + dy * -sin) / this.scale.x + this.anchor.x * this.width;
        var by  = Math.floor(dx * sin + dy * cos) / this.scale.y + this.anchor.y * this.height;
        return this.bitmap.getAlphaPixel(bx, by) === 0;
    };

    Sprite_Picture.prototype.isValidTransparent = function() {
        var transparent = $gameScreen.getPictureTransparent(this._pictureId);
        return transparent !== null ? transparent : paramTransparentConsideration;
    };

    Sprite_Picture.prototype.screenWidth = function() {
        return (this.width || 0) * this.scale.x;
    };

    Sprite_Picture.prototype.screenHeight = function() {
        return (this.height || 0) * this.scale.y;
    };

    Sprite_Picture.prototype.screenX = function() {
        return (this.x || 0) - this.anchor.x * this.screenWidth();
    };

    Sprite_Picture.prototype.screenY = function() {
        return (this.y || 0) - this.anchor.y * this.screenHeight();
    };

    Sprite_Picture.prototype.minX = function() {
        return Math.min(this.screenX(), this.screenX() + this.screenWidth());
    };

    Sprite_Picture.prototype.minY = function() {
        return Math.min(this.screenY(), this.screenY() + this.screenHeight());
    };

    Sprite_Picture.prototype.maxX = function() {
        return Math.max(this.screenX(), this.screenX() + this.screenWidth());
    };

    Sprite_Picture.prototype.maxY = function() {
        return Math.max(this.screenY(), this.screenY() + this.screenHeight());
    };

    Sprite_Picture.prototype.isTouchPosInRect = function() {
        if (this.isTouchPosInFrameWindow()) return true;
        var dx  = this.getTouchScreenX() - this.x;
        var dy  = this.getTouchScreenY() - this.y;
        var sin = Math.sin(-this.rotation);
        var cos = Math.cos(-this.rotation);
        var rx  = this.x + Math.floor(dx * cos + dy * -sin);
        var ry  = this.y + Math.floor(dx * sin + dy * cos);
        return (rx >= this.minX() && rx <= this.maxX() && ry >= this.minY() && ry <= this.maxY());
    };

    Sprite_Picture.prototype.isTouchPosInFrameWindow = function() {
        if (!this._frameWindow) return false;
        var frame = this._frameWindow;
        var x     = this.getTouchScreenX();
        var y     = this.getTouchScreenY();
        return frame.x <= x && frame.x + frame.width >= x && frame.y <= y && frame.y + frame.height >= y;
    };

    Sprite_Picture.prototype.isTouchable = function() {
        return this.bitmap && this.visible && this.scale.x !== 0 && this.scale.y !== 0;
    };

    Sprite_Picture.prototype.isTriggered = function() {
        return this.isTouchEvent(TouchInput.isTriggered);
    };

    Sprite_Picture.prototype.isCancelled = function() {
        return this.isTouchEvent(TouchInput.isCancelled);
    };

    Sprite_Picture.prototype.isLongPressed = function() {
        return this.isTouchEvent(TouchInput.isLongPressed);
    };

    Sprite_Picture.prototype.isPressed = function() {
        return this.isTouchEvent(TouchInput.isPressed);
    };

    Sprite_Picture.prototype.isReleased = function() {
        return this.isTouchEvent(TouchInput.isReleased);
    };

    Sprite_Picture.prototype.isRepeated = function() {
        return this.isTouchEvent(TouchInput.isRepeated);
    };

    Sprite_Picture.prototype.isOnFocus = function() {
        return this._onMouse;
    };

    Sprite_Picture.prototype.isOutFocus = function() {
        return this._outMouse;
    };

    Sprite_Picture.prototype.isMoved = function() {
        return this.isTouchEvent(TouchInput.isMoved);
    };

    Sprite_Picture.prototype.isMovedAndPressed = function() {
        return this.isTouchEvent(TouchInput.isMoved) && TouchInput.isPressed();
    };

    Sprite_Picture.prototype.isWheelTriggered = function() {
        return this.isTouchEvent(TouchInput.isWheelTriggered);
    };

    Sprite_Picture.prototype.isDoubleTriggered = function() {
        return this.isTouchEvent(TouchInput.isDoubleTriggered);
    };

    Sprite_Picture.prototype.isTouchEvent = function(triggerFunc) {
        return this.isTouchable() && triggerFunc.call(TouchInput) && this.isTouchPosInRect();
    };

    Sprite_Picture.prototype.getTouchScreenX = function() {
        return $gameScreen.disConvertPositionX(TouchInput.x);
    };

    Sprite_Picture.prototype.getTouchScreenY = function() {
        return $gameScreen.disConvertPositionY(TouchInput.y);
    };

    Sprite_Picture.prototype.isIdEquals = function(pictureId) {
        return this._pictureId === pictureId;
    };

    //=============================================================================
    // Input
    //  Links picture click to key input.
    //=============================================================================
    Input._bindKeyStateFrames = new Map();
    Input.bindKeyState        = function(name) {
        this._currentState[name] = true;
        this._bindKeyStateFrames.set(name, 5);
    };

    var _Input_update = Input.update;
    Input.update      = function() {
        _Input_update.apply(this, arguments);
        this._updateBindKeyState();
    };

    Input._updateBindKeyState = function() {
        this._bindKeyStateFrames.forEach(function(frame, keyName) {
            frame--;
            if (frame === 0 || !this._currentState[keyName]) {
                this._currentState[keyName] = false;
                this._bindKeyStateFrames.delete(keyName);
            } else {
                this._bindKeyStateFrames.set(keyName, frame);
            }
        }, this);
    };

    //=============================================================================
    // TouchInput
    //  Implements wheel click, double click, etc.
    //=============================================================================
    TouchInput.keyDoubleClickInterval = 300;
    TouchInput._pressedDistance       = 0;
    TouchInput._prevX                 = -1;
    TouchInput._prevY                 = -1;

    Object.defineProperty(TouchInput, 'pressedDistance', {
        get         : function() {
            return this._pressedDistance;
        },
        configurable: true
    });

    TouchInput.suppressEvents = function() {
        this._triggered       = false;
        this._cancelled       = false;
        this._released        = false;
        this._wheelTriggered  = false;
        this._doubleTriggered = false;
    };

    TouchInput._onMouseMove = function(event) {
        var x = Graphics.pageToCanvasX(event.pageX);
        var y = Graphics.pageToCanvasY(event.pageY);
        this._onMove(x, y);
    };

    var _TouchInput_clear = TouchInput.clear;
    TouchInput.clear      = function() {
        _TouchInput_clear.apply(this, arguments);
        this._events.wheelTriggered  = false;
        this._events.doubleTriggered = false;
    };

    var _TouchInput_update = TouchInput.update;
    TouchInput.update      = function() {
        _TouchInput_update.apply(this, arguments);
        this._wheelTriggered         = this._events.wheelTriggered;
        this._doubleTriggered        = this._events.doubleTriggered;
        this._events.wheelTriggered  = false;
        this._events.doubleTriggered = false;
    };

    TouchInput.isWheelTriggered = function() {
        return this._wheelTriggered;
    };

    TouchInput.isDoubleTriggered = function() {
        return this._doubleTriggered;
    };

    var _TouchInput_onMiddleButtonDown = TouchInput._onMiddleButtonDown;
    TouchInput._onMiddleButtonDown     = function(event) {
        _TouchInput_onMiddleButtonDown.apply(this, arguments);
        var x = Graphics.pageToCanvasX(event.pageX);
        var y = Graphics.pageToCanvasY(event.pageY);
        if (Graphics.isInsideCanvas(x, y)) {
            this._onWheelTrigger(x, y);
        }
    };

    TouchInput._onWheelTrigger = function(x, y) {
        this._events.wheelTriggered = true;
        this._x                     = x;
        this._y                     = y;
    };

    var _TouchInput_onTrigger = TouchInput._onTrigger;
    TouchInput._onTrigger     = function(x, y) {
        if (this._date && Date.now() - this._date < this.keyDoubleClickInterval)
            this._events.doubleTriggered = true;
        this._pressedDistance = 0;
        this._prevX           = x;
        this._prevY           = y;
        _TouchInput_onTrigger.apply(this, arguments);
    };

    var _TouchInput_onMove = TouchInput._onMove;
    TouchInput._onMove     = function(x, y) {
        if (this.isPressed()) this._pressedDistance = Math.abs(this._prevX - x) + Math.abs(this._prevY - y);
        this._prevX = x;
        this._prevY = y;
        _TouchInput_onMove.apply(this, arguments);
    };

    var _TouchInput_onRelease = TouchInput._onRelease;
    TouchInput._onRelease     = function(x, y) {
        this._pressedDistance = 0;
        this._prevX           = x;
        this._prevY           = y;
        _TouchInput_onRelease.apply(this, arguments);
    };
})();
