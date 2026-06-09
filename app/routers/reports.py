from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from io import BytesIO
from openpyxl import Workbook
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import HistoricalValue, Tag
router=APIRouter(prefix='/reports')
@router.get('')
def index(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    return templates.TemplateResponse('reports.html', {'request':request,'user':user,'tags':db.query(Tag).all()})
@router.get('/export.xlsx')
def export(db:Session=Depends(get_db), user=Depends(require_user)):
    rows=db.query(HistoricalValue, Tag).join(Tag, HistoricalValue.tag_id==Tag.id).order_by(HistoricalValue.timestamp.desc()).limit(5000).all()
    wb=Workbook(); ws=wb.active; ws.title='Historical Data'; ws.append(['Timestamp','Tag','Value','Unit','Source'])
    for hv,tag in rows: ws.append([hv.timestamp.strftime('%Y-%m-%d %H:%M:%S'), tag.display_name, hv.value, tag.unit, hv.source])
    bio=BytesIO(); wb.save(bio); bio.seek(0)
    return StreamingResponse(bio, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename=iiot_report.xlsx'})
