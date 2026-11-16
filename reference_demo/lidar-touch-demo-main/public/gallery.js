(function(root){
  class TouchGallery {
    constructor(stage,pictures){
      this.pictures=pictures;this.selected=-1;this.playing=false;this.imageLeft=false;this.nextAt=0;this.contacts=new Map();this.edits=JSON.parse(localStorage.getItem('s3-slide-text')||'{}');
      const panel=document.createElement('section');panel.className='gallery-layer hidden';panel.id='gallery-layer';panel.setAttribute('aria-label','Interactive picture slideshow');
      panel.innerHTML=`<div class="gallery-header"><div><span class="eyebrow">TOUCH TO EXPLORE</span><h2>Every picture has a story.</h2></div><div class="gallery-tools"><button data-sensor-action="gallery-home" aria-label="Show all thumbnails">All pictures</button><button data-sensor-action="gallery-swap" aria-label="Swap image and text sides">Swap sides ⇄</button><button data-sensor-action="gallery-play" aria-label="Start automatic slideshow">▶ Slideshow</button></div></div><div class="gallery-thumbnails"></div><article class="gallery-detail hidden"><div class="gallery-copy"><span class="gallery-number"></span><span class="eyebrow">THE LANDSCAPE COLLECTION</span><h2></h2><p></p><div class="gallery-tags"><span>TOUCH TO DISCOVER</span><span>INTERACTIVE STORY</span></div><span class="gallery-copy-hint">Touch the picture to hide or reveal its story.</span></div><button class="gallery-image" data-sensor-action="gallery-info" aria-label="Toggle information about this picture"><img alt=""><span>TOUCH TO REVEAL THE STORY ↗</span></button></article><div class="gallery-pagination"><button data-sensor-action="gallery-prev" aria-label="Previous picture">← Previous</button><span class="gallery-counter">SELECT A PICTURE TO BEGIN</span><button data-sensor-action="gallery-next" aria-label="Next picture">Next →</button></div>`;
      stage.append(panel);this.panel=panel;
      panel.addEventListener('click',event=>{const button=event.target.closest('[data-sensor-action]');if(!button)return;const action=button.dataset.sensorAction;if(action.startsWith('slide-'))this.select(Number(action.slice(6)));else if(action==='gallery-home')this.home();else if(action==='gallery-prev')this.select((this.selected-1+this.pictures.length)%this.pictures.length);else if(action==='gallery-next')this.select((this.selected+1)%this.pictures.length);else if(action==='gallery-swap'){this.imageLeft=!this.imageLeft;this.render();}else if(action==='gallery-play'){this.playing=!this.playing;if(this.selected<0)this.select(0);this.render();}else if(action==='gallery-info')panel.querySelector('.gallery-detail').classList.toggle('hide-story');this.nextAt=performance.now()+8000;});
      this.render();
    }
    data(i){return {...this.pictures[i],...(this.edits[i]||{})};}
    saveText(i,title,description){this.edits[i]={title:title.trim()||this.pictures[i].title,description:description.trim()||this.pictures[i].description};localStorage.setItem('s3-slide-text',JSON.stringify(this.edits));this.render();}
    setPictures(pictures){this.pictures=pictures;if(this.selected>=pictures.length)this.selected=-1;this.render();}
    setActive(active){this.panel.classList.toggle('hidden',!active);if(!active)this.contacts.clear();}
    home(){this.selected=-1;this.playing=false;this.render();}
    select(index){this.selected=index;this.nextAt=performance.now()+8000;this.panel.querySelector('.gallery-detail').classList.remove('hide-story');this.render();}
    render(){
      const thumbnails=this.panel.querySelector('.gallery-thumbnails');thumbnails.replaceChildren();
      this.pictures.forEach((_picture,i)=>{const p=this.data(i),button=document.createElement('button');button.className='gallery-thumbnail';button.dataset.sensorAction='slide-'+i;const image=document.createElement('img');image.src=p.src;image.alt=p.title;const caption=document.createElement('span'),number=document.createElement('small'),title=document.createElement('strong'),arrow=document.createElement('b');number.textContent=String(i+1).padStart(2,'0')+' / EXPLORE';title.textContent=p.title;arrow.textContent='↗';caption.append(number,title,arrow);button.append(image,caption);thumbnails.append(button);});
      const detail=this.panel.querySelector('.gallery-detail');detail.classList.toggle('hidden',this.selected<0);thumbnails.classList.toggle('hidden',this.selected>=0);detail.classList.toggle('image-left',this.imageLeft);
      if(this.selected>=0){const p=this.data(this.selected);detail.querySelector('img').src=p.src;detail.querySelector('img').alt=p.title;detail.querySelector('h2').textContent=p.title;detail.querySelector('.gallery-copy>p').textContent=p.description;detail.querySelector('.gallery-number').textContent=String(this.selected+1).padStart(2,'0');}
      this.panel.querySelector('.gallery-counter').textContent=this.selected<0?'SELECT A PICTURE TO BEGIN':`${String(this.selected+1).padStart(2,'0')} / ${String(this.pictures.length).padStart(2,'0')}`;
      const play=this.panel.querySelector('[data-sensor-action="gallery-play"]');play.textContent=this.playing?'Ⅱ Pause slideshow':'▶ Slideshow';play.setAttribute('aria-label',this.playing?'Pause automatic slideshow':'Start automatic slideshow');
    }
    tick(now){if(this.playing&&this.selected>=0&&now>=this.nextAt)this.select((this.selected+1)%this.pictures.length);}
    sensorTouches(touches,stage,now){
      const bounds=stage.getBoundingClientRect(),seen=new Set();
      for(const touch of touches){seen.add(touch.id);let held=this.contacts.get(touch.id);if(held?.fired)continue;const x=bounds.left+touch.u*bounds.width,y=bounds.top+touch.v*bounds.height;const target=document.elementFromPoint(x,y)?.closest('button[data-sensor-action],.display-dock button');if(!target||target.disabled){this.contacts.delete(touch.id);continue;}if(!held||held.target!==target){held={target,since:now,fired:false};this.contacts.set(touch.id,held);}if(now-held.since>180){held.fired=true;target.click();this.nextAt=now+8000;}}
      for(const id of this.contacts.keys())if(!seen.has(id))this.contacts.delete(id);
    }
  }
  root.TouchGallery=TouchGallery;
})(window);
