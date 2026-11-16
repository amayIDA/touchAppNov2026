const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('touchDesktop',{
  toggleFullscreen:()=>ipcRenderer.invoke('desktop:fullscreen'),
  isFullscreen:()=>ipcRenderer.invoke('desktop:is-fullscreen'),
  onFullscreen:callback=>ipcRenderer.on('desktop:fullscreen',(_event,value)=>callback(value))
});
