const fs=require('node:fs');const path=require('node:path');
module.exports=async context=>{
  const folder=path.join(context.packager.projectDir,'.build');fs.mkdirSync(folder,{recursive:true});
  const existing=path.join(context.packager.projectDir,'data','config.json');
  const initial=fs.existsSync(existing)?JSON.parse(fs.readFileSync(existing,'utf8')):{transport:'tuio',address:'127.0.0.1',port:3333,baud:1000000,corners:null};
  fs.writeFileSync(path.join(folder,'initial-sensor-config.json'),JSON.stringify(initial,null,2));
};
