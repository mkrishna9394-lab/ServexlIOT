from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Site, Gateway, Sensor, Tag
router=APIRouter(prefix='/devices')
@router.get('')
def index(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    return templates.TemplateResponse('devices.html', {'request':request,'user':user,'sites':db.query(Site).all(),'gateways':db.query(Gateway).all(),'sensors':db.query(Sensor).all(),'tags':db.query(Tag).all()})
@router.post('/gateway/add')
def gateway(
    site_id: int = Form(...),
    code: str = Form(...),
    mqtt_host: str = Form('localhost'),
    mqtt_port: int = Form(1883),
    mqtt_username: str = Form(''),
    mqtt_password: str = Form(''),
    mqtt_topic: str = Form('#'),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    db.add(Gateway(
        site_id=site_id,
        code=code,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        mqtt_topic=mqtt_topic
    ))
    db.commit()
    return RedirectResponse('/devices', 303)
@router.post('/sensor/add')
def sensor(gateway_id:int=Form(...), code:str=Form(...), name:str=Form(...), sensor_type:str=Form('general'), db:Session=Depends(get_db), user=Depends(require_user)):
    db.add(Sensor(gateway_id=gateway_id,code=code,name=name,sensor_type=sensor_type)); db.commit(); return RedirectResponse('/devices',303)
@router.post('/tag/add')
def tag(sensor_id:int=Form(...), key:str=Form(...), display_name:str=Form(...), unit:str=Form(''), low_limit:float|None=Form(None), high_limit:float|None=Form(None), db:Session=Depends(get_db), user=Depends(require_user)):
    db.add(Tag(sensor_id=sensor_id,key=key,display_name=display_name,unit=unit,low_limit=low_limit,high_limit=high_limit)); db.commit(); return RedirectResponse('/devices',303)
