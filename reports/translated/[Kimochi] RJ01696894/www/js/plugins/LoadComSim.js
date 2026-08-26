//=============================================================================
// LoadComSim.js
//=============================================================================

/*:ja
 * @plugindesc ver1.00 メニューコマンドにロードを追加します。
 * @author まっつＵＰ
 * 
 * @param loadtext
 * @desc コマンド「ロード」のコマンド名です。
 * @default ロード
 *
 * @help
 * 
 * RPG, let's have a smile...
 * 
 * Please read the help and parameter explanations carefully before using.
 * 
 * The 'Load' command will be unselectable during event testing or when there is no save data.
 * 
 * Terms of Use (Last Updated: 2019/9/3):
 * This work is provided under the Material Commons License Blue.
 * https://materialcommons.tk/mtcm-b-summary/
 * Credit: matsuUP
 * 
 */

(function() {
    
    var parameters = PluginManager.parameters('LoadComSim');
    var LCSloadtext = String(parameters['loadtext'] || 'Load');

    var _Scene_Menu_createCommandWindow = Scene_Menu.prototype.createCommandWindow;
    Scene_Menu.prototype.createCommandWindow = function() {
    _Scene_Menu_createCommandWindow.call(this);
    this._commandWindow.setHandler('load', this.commandLoad.bind(this));
    };

    Scene_Menu.prototype.commandLoad = function() { //new
    SceneManager.push(Scene_Load);
    };

    var _Window_MenuCommand_addSaveCommand = Window_MenuCommand.prototype.addSaveCommand;
    Window_MenuCommand.prototype.addSaveCommand = function() {
    _Window_MenuCommand_addSaveCommand.call(this);
     var enabled = this.isLoadEnabled();
     this.addCommand(LCSloadtext, 'load', enabled);
    };
      
    Window_MenuCommand.prototype.isLoadEnabled = function() { //new
    if(DataManager.isEventTest()) return false; // This line checks if it's during event testing.
    return DataManager.isAnySavefileExists();
    };

})();
