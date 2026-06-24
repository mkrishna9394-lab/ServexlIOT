from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.services.event_logger import log_event
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import (
    Customer,
    Site,
    Gateway,
    Sensor,
    Tag,
    LiveValue,
    HistoricalValue,
    Alert,
)

router = APIRouter(prefix="/customers")


@router.get("")
def index(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    return templates.TemplateResponse(
        "customers.html",
        {
            "request": request,
            "user": user,
            "customers": db.query(Customer).all(),
            "sites": db.query(Site).all(),
        }
    )


@router.post("/add")
def add(
    name: str = Form(...),
    contact_email: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    db.add(Customer(name=name, contact_email=contact_email))
    db.commit()

    log_event(db, user, "Customers", "Add Customer", f"Customer {name} added")

    return RedirectResponse("/customers", 303)


@router.post("/update")
def update_customer(
    customer_id: int = Form(...),
    name: str = Form(...),
    contact_email: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer:
        customer.name = name
        customer.contact_email = contact_email
        db.commit()

        log_event(db, user, "Customers", "Update Customer", f"Customer {customer.name} updated")


    return RedirectResponse("/customers", 303)


@router.post("/delete")
def delete_customer(
    customer_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    sites = db.query(Site).filter(Site.customer_id == customer_id).all()

    for site in sites:
        delete_site_data(db, site.id)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer:
        db.delete(customer)
        db.commit()

        log_event(db, user, "Customers", "Delete Customer", f"Customer deleted")

    return RedirectResponse("/customers", 303)


@router.post("/site/add")
def add_site(
    customer_id: int = Form(...),
    name: str = Form(...),
    location: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    db.add(Site(customer_id=customer_id, name=name, location=location))
    db.commit()

    log_event(db, user, "Customers", "Add Site", f"Site {name} added")

    return RedirectResponse("/customers", 303)


@router.post("/site/update")
def update_site(
    site_id: int = Form(...),
    customer_id: int = Form(...),
    name: str = Form(...),
    location: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()

    if site:
        site.customer_id = customer_id
        site.name = name
        site.location = location
        db.commit()

        log_event(db, user, "Customers", "Update Site", f"Site {site.name} updated")

    return RedirectResponse("/customers", 303)


@router.post("/site/delete")
def delete_site(
    site_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    delete_site_data(db, site_id)
    return RedirectResponse("/customers", 303)


def delete_site_data(db: Session, site_id: int):
    gateways = db.query(Gateway).filter(Gateway.site_id == site_id).all()

    for gateway in gateways:
        sensors = db.query(Sensor).filter(Sensor.gateway_id == gateway.id).all()

        for sensor in sensors:
            tags = db.query(Tag).filter(Tag.sensor_id == sensor.id).all()

            for tag in tags:
                db.query(LiveValue).filter(LiveValue.tag_id == tag.id).delete()
                db.query(HistoricalValue).filter(HistoricalValue.tag_id == tag.id).delete()
                db.query(Alert).filter(Alert.tag_id == tag.id).delete()
                db.delete(tag)

            db.delete(sensor)

        db.delete(gateway)

    site = db.query(Site).filter(Site.id == site_id).first()

    if site:
        db.delete(site)

    db.commit()
    log_event(db, user, "Customers", "Delete Site", f"Site deleted")

