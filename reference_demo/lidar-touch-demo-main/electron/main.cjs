const {app,BrowserWindow,ipcMain,dialog}=require('electron');
const fs=require('node:fs');
const path=require('node:path');
const {once}=require('node:events');
let window,backend=null,quitting=false;
const single=app.requestSingleInstanceLock();
if(!single)app.quit();
else{
  app.on('second-instance',()=>{if(window){if(window.isMinimized())window.restore();window.show();window.focus();}});
  app.whenReady().then(async()=>{
    const dataDir=path.join(app.getPath('userData'),'sensor');fs.mkdirSync(dataDir,{recursive:true});
    // Adopt a running local demo so the same live sensor/calibration is retained.
    let url='http://127.0.0.1:4173';let current;
    try{const r=await fetch(url+'/api/config',{signal:AbortSignal.timeout(1200)});current=await r.json();if(!current.config||!current.state)throw Error('Different service');}
    catch{
      const previous=app.isPackaged?path.join(process.resourcesPath,'initial-sensor-config.json'):path.join(__dirname,'..','data','config.json'),destination=path.join(dataDir,'config.json');
      if(!fs.existsSync(destination)&&fs.existsSync(previous))fs.copyFileSync(previous,destination);
      process.env.DATA_DIR=dataDir;process.env.PORT='0';backend=require('../server.js');
      if(!backend.server.listening)await once(backend.server,'listening');
      url='http://127.0.0.1:'+backend.server.address().port;
      current=await(await fetch(url+'/api/config')).json();
    }
    fs.writeFileSync(path.join(dataDir,'config.json'),JSON.stringify(current.config,null,2));
    if(current.state.status==='disconnected'&&current.config.address){
      await fetch(url+'/api/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(current.config)}).catch(()=>{});
    }
    window=new BrowserWindow({width:1440,height:900,minWidth:800,minHeight:600,title:'S3 Touch Studio',backgroundColor:'#090d11',fullscreen:true,autoHideMenuBar:true,show:false,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
    window.setMenuBarVisibility(false);
    window.webContents.setWindowOpenHandler(()=>({action:'deny'}));
    window.webContents.on('will-navigate',(event,destination)=>{if(new URL(destination).origin!==new URL(url).origin)event.preventDefault();});
    window.webContents.on('before-input-event',(event,input)=>{if(input.type==='keyDown'&&input.key==='F11'){event.preventDefault();window.setFullScreen(!window.isFullScreen());}if(input.type==='keyDown'&&input.key==='Escape'&&!input.control&&!input.alt)window.setFullScreen(false);});
    ipcMain.handle('desktop:fullscreen',()=>{window.setFullScreen(!window.isFullScreen());return window.isFullScreen();});
    ipcMain.handle('desktop:is-fullscreen',()=>window.isFullScreen());
    window.on('enter-full-screen',()=>window.webContents.send('desktop:fullscreen',true));window.on('leave-full-screen',()=>window.webContents.send('desktop:fullscreen',false));
    await window.loadURL(url+'/?display=1&desktop=1&experience=gallery');window.show();
  }).catch(error=>{dialog.showErrorBox('S3 Touch Studio could not start',error.message);app.quit();});
  app.on('window-all-closed',()=>app.quit());
  app.on('before-quit',event=>{if(backend&&!quitting){event.preventDefault();quitting=true;backend.closeServer().finally(()=>app.quit());}});
}
