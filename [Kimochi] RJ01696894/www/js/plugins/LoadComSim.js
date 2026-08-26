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
 * RPGで笑顔を・・・
 * 
 * このヘルプとパラメータの説明をよくお読みになってからお使いください。
 * 
 * コマンド「ロード」はイベントテスト中またはセーブデータがないときは選択不能になります。
 * 
 * 利用規約(2019/9/3変更)：
 * この作品は マテリアル・コモンズ・ライセンス・ブルーの下に提供されています。
 * https://materialcommons.tk/mtcm-b-summary/
 * クレジット表示：まっつUP
 * 
 */

(function() {
    
    var parameters = PluginManager.parameters('LoadComSim');
    var LCSloadtext = String(parameters['loadtext'] || 'ロード');

    var _Scene_Menu_createCommandWindow = Scene_Menu.prototype.createCommandWindow;
    Scene_Menu.prototype.createCommandWindow = function() {
    _Scene_Menu_createCommandWindow.call(this);
    this._commandWindow.setHandler('load', this.commandLoad.bind(this));
    };

    Scene_Menu.prototype.commandLoad = function() { //新規
    SceneManager.push(Scene_Load);
    };

    var _Window_MenuCommand_addSaveCommand = Window_MenuCommand.prototype.addSaveCommand;
    Window_MenuCommand.prototype.addSaveCommand = function() {
    _Window_MenuCommand_addSaveCommand.call(this);
     var enabled = this.isLoadEnabled();
     this.addCommand(LCSloadtext, 'load', enabled);
    };
      
    Window_MenuCommand.prototype.isLoadEnabled = function() { //新規
    if(DataManager.isEventTest()) return false; //この行はイベントテスト中かどうか判定しています。
    return DataManager.isAnySavefileExists();
    };

})();
