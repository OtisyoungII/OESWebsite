const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../static/js/eyeball-motion.js'),'utf8');
 const {MotionArbiter}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
 const core={left:100,top:100,right:200,bottom:200,width:100,height:100};
 let t=0;let m;let count=0;
 function test(name,fn){m=new MotionArbiter(()=>t);t=0;fn();count++;console.log('PASS',name);}
 function sample(a,b,target){m.observe(a,core,target);t=50;m.observe(b,core,target);}
 test('casual pass requires obstruction',()=>{sample({x:20,y:90},{x:80,y:90});assert.equal(m.decide().movement_allowed,false);});
 test('direct approach holds section and avoidance',()=>{sample({x:20,y:150},{x:70,y:150});assert.equal(m.decide().state,'approached');assert.equal(m.decide({reason:'section-change'}).movement_allowed,false);});
 test('pointerdown locks until matching release',()=>{m.down(7);m.up(8);assert.equal(m.decide({reason:'section-change'}).state,'engaged');m.up(7);t=1000;assert.equal(m.decide({reason:'section-change'}).movement_allowed,true);});
 test('explicit drag and docking remain allowed',()=>{m.down(7);for(const reason of ['drag','manual-dock'])assert.equal(m.decide({reason}).movement_allowed,true);});
 const target={left:170,top:100,right:270,bottom:200,width:100,height:100};
 test('real overlapping target trajectory may relocate',()=>{sample({x:220,y:100},{x:220,y:140},target);assert.equal(m.decide().movement_allowed,true);assert.equal(m.decide().state,'avoiding');});
 test('target without overlap stays silent',()=>{sample({x:220,y:100},{x:220,y:140},{...target,left:210,right:270});assert.equal(m.decide().movement_allowed,false);});
 test('follow after relocation holds and cooldown bounds repeated fleeing',()=>{m.relocated();assert.equal(m.decide().state,'available');sample({x:20,y:150},{x:70,y:150});assert.equal(m.decide().state,'approached');t=2000;assert.equal(m.decide({reason:'section-change'}).movement_allowed,false);t=3100;assert.equal(m.decide({reason:'section-change'}).movement_allowed,true);});
 test('chat outranks avoidance',()=>assert.equal(m.decide({chat:true}).state,'engaged'));
 test('invitation outranks avoidance',()=>assert.equal(m.decide({invitation:true}).movement_allowed,false));
 test('AI context cannot override policy',()=>assert.equal(m.decide({context:{state:'avoiding',movement_allowed:true}}).movement_allowed,false));
 test('in-flight automatic move stops on engagement',()=>{m.down(1);assert.equal(m.decide({continuing:true}).movement_allowed,false);});
 test('serious and suppression hold',()=>{assert.equal(m.decide({serious:true}).state,'serious');assert.equal(m.decide({suppressed:true}).state,'suppressed');});
 test('stale trajectory cannot authorize avoidance',()=>{sample({x:220,y:100},{x:220,y:140},target);t=400;assert.equal(m.decide().movement_allowed,false);});
 test('Core travel under pointer is not visitor approach',()=>{
  m.observe({x:220,y:140},core);t=50;
  m.observe({x:220,y:140},{...core,left:170,right:270},null,true);
  assert.notEqual(m.decide({continuing:true}).state,'approached');
  m.down(1);assert.equal(m.decide({continuing:true}).movement_allowed,false);
 });
 console.log(`${count} motion policy tests passed`);
})().catch(e=>{console.error(e);process.exitCode=1});
