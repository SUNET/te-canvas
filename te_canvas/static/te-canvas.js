/**
 * Javascript related to TimeEdit integration.
 * These scripts are based on the work done by the Canvas project @ LU, CALU.
 **/

// All TimeEdit event titles must contain this string, so we can distinguish them from normal events
// This is a hidden unicode character, a zero width whitespace
const TITLE_TAG = '​';
const AGENDA_ITEM_CLASSNAME = 'agenda-event__item-container';
const CALENDAR_ITEM_CLASSNAME = "fc-event";

const initLoading = () => {
    setTimeout(() => {
        blockTEEventEditing();
    }, 700);
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLoading);
} else {
    initLoading();
}

const hideButtonsFromEventDetailsFooter = () => {
    const currentEvent = document.querySelector("#event-details-trap-focus")
    if (currentEvent != null) {
        const title = currentEvent.querySelector(".details_title")
        if (title.innerText.indexOf(TITLE_TAG) > -1) {
            const footer = currentEvent.querySelector(".event-details-footer");
            footer.style.display = "none";
        }
    }
}

const burstHideButtonsFromEventDetailsFooter = () => {
    [50, 250, 800].forEach(timeout => {
        setTimeout(() => {
            hideButtonsFromEventDetailsFooter();
        }, timeout);
    });
}

const hideButtonsOnContainerClass = (containerClass, trialNumber = 0) => {
    //timing issue here sometimes. It CAN take a while for containers to be existing (seen on agenda view)
    var containers = document.getElementsByClassName(containerClass);
    if (containers && containers.length > 0) {
        for (var i = 0; i < containers.length; i++) {
            var container = containers[i];
            if (container.innerText.indexOf(TITLE_TAG) > -1) {
                container.addEventListener('click', burstHideButtonsFromEventDetailsFooter);
            }
        }
    }

    else if (trialNumber < 10) {
        setTimeout(function () {
            hideButtonsOnContainerClass(containerClass, ++trialNumber);
        }, 200);

    }
    updateEventBackgrounds();
}

const fcDisableEvents = (events) => {
    try {
        let updateEvents = false;
        events.forEach(ce => {
            if (ce.title.indexOf(TITLE_TAG) > -1) {
                if (ce.editable == true || ce.droppable == true) {
                    ce.editable = false;
                    ce.droppable = false;
                    updateEvents = true;
                }
            }
        });
        if (updateEvents) {
            $('.calendar').fullCalendar("updateEvents", events);
        }
    }
    catch (error) {
        console.error('fullcalendarDisableEvents failed', error, events);
    }
}

const hideButtonsOnAgendaView = () => {
    if (window.location.href.indexOf("view_name=agenda") > -1) {
        hideButtonsOnContainerClass(AGENDA_ITEM_CLASSNAME);
    }
}

const disableFcWithDelay = () => {
    var cal = $('.calendar').fullCalendar('getCalendar');
    teEvents = cal.clientEvents().filter(event => event?.title?.includes(TITLE_TAG));
    if (teEvents.length === 0) {
        return;
    }
    let alreadyDone = false;
    if (cal) {
        [50, 250, 1000, 3000, 10000].forEach(timeout => {
            setTimeout(() => {
                if (!alreadyDone && cal.clientEvents().length > 0) {
                    fcDisableEvents(cal.clientEvents());
                    hideButtonsOnContainerClass(CALENDAR_ITEM_CLASSNAME);
                    alreadyDone = true;
                }
            }, timeout);
        });
    }
}

triggerHidingOfButtons = (event_details) => {
    if (event_details.innerText.indexOf(TITLE_TAG) > -1) {
        burstHideButtonsFromEventDetailsFooter();
    }
}

const hideButtonsWhenOpeningFromSyllabus = () => {
    if ((window.location.href.indexOf("calendar?") > -1) && (window.location.href.indexOf("event_id=") > -1)) {
        var eventDetails = document.getElementById('event-details-trap-focus');
        let foundEventDetails = false;
        [100, 500, 1000].forEach(timeout => {
            setTimeout(() => {
                eventDetails = document.getElementById('event-details-trap-focus');
                if (eventDetails) {
                    foundEventDetails = true;
                    triggerHidingOfButtons(eventDetails);
                }
            }, timeout);
        });
    }
}

const hideLinksWhenViewingEventInCourse = () => {
    if (window.location.href.indexOf("/calendar_events/") > -1) {
        let eventContainer = document.getElementById("full_calendar_event");
        if (eventContainer.innerText.indexOf(TITLE_TAG) > -1) {
            let actionList = document.querySelector("#sidebar_content > .page-action-list");
            let sidebarLinks = actionList.querySelectorAll("a");
            let linksToRemove = new Array();
            for (let i = 0; i < sidebarLinks.length; i++) {
                if (sidebarLinks[i].href.indexOf("/edit?") > -1 || sidebarLinks[i].className.indexOf("delete_event_link") > -1) {
                    linksToRemove.push(sidebarLinks[i]);
                }
            }
            linksToRemove.forEach(link => {
                link.remove();
            });
        }
    }
}

const handleAgendaView = () => {
    // We need to give window.location.href some time to update
    let handled = false;
    [100, 300, 700].forEach(timeout => {
        setTimeout(() => {
            if (!handled && window.location.href.indexOf("view_name=agenda") > -1) {
                hideButtonsOnAgendaView();
                handled = true;
            }
        }, timeout);
    });
    updateEventBackgrounds();
}

const addEventListenersToCalendar = () => {

    document.getElementById("agenda").onclick = () => {
        handleAgendaView();
        disableFcWithDelay();
    }

    //minical is the small calendar in upper right corner
    document.getElementById("minical").onclick = () => {
        handleAgendaView();
        disableFcWithDelay();
    }

    //calendars-context list is the list of available calendars to the right
    document.getElementById("calendars-context-list").onclick = () => {
        handleAgendaView();
        disableFcWithDelay();
    }

    var calNav = document.getElementsByClassName('calendar_navigator') //Calendar navigator is buttons for '<', '>' and 'today'
    if (calNav.length > 0) {
        calNav[0].onclick = () => {
            handleAgendaView();
            disableFcWithDelay();
        }
    }

}

const blockTEEventEditing = () => {
    //Canvas uses FullCalendar v3.10.5 with some customizations
    //https://fullcalendar.io/docs/v3

    //Some views are not default fullcalendar views. When not, we have to hack buttons and stuff away.
    //In agenda view 'eventAfterAllRender' does not trigger. This is why we have a lot of button removal scripts

    try {
        if (!(window.location.href.indexOf("calendar") > -1)) {
            return
        }
        hideButtonsWhenOpeningFromSyllabus();
        if (window.location.href.indexOf("/calendar_events/") > -1) {
            hideLinksWhenViewingEventInCourse();
            return;
        }

        let cal;
        const intervalId = setInterval(function () {
            try {
                cal = $('.calendar').fullCalendar('getCalendar');
                cal.on('eventAfterAllRender', function () {
                    disableFcWithDelay();
                    updateEventBackgrounds();
                });
                handleAgendaView();
                addEventListenersToCalendar();
                disableFcWithDelay();
                clearInterval(intervalId);
            } catch (err) {
                console.error(err)
            }
        }, 300)

    } catch (error) {
        console.error('blockTEEventEditing', error);
    }
}

const updateEventBackgrounds = () => {
    if (window.location.href.indexOf("view_name=agenda") > -1) {
        let agendaItems = document.getElementsByClassName(AGENDA_ITEM_CLASSNAME);
        if (agendaItems.length > 0) {
            for (let i = 0; i < agendaItems.length; i++) {
                if (agendaItems[i].innerText.indexOf(TITLE_TAG) > -1)
                    agendaItems[i].classList.add("teEvent", "teAgendaEvent");
            }
        }
    }
    else {
        let eventDivs = document.getElementsByClassName(CALENDAR_ITEM_CLASSNAME);
        if (eventDivs.length > 0) {
            for (let i = 0; i < eventDivs.length; i++) {
                if (eventDivs[i].innerText.indexOf(TITLE_TAG) > -1) {
                    eventDivs[i].classList.add("teEvent");
                }
            }
        }
    }
}