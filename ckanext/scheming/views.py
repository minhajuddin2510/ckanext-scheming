
from flask import Response, Blueprint
from flask.views import MethodView
from werkzeug.datastructures import MultiDict

from ckan.plugins.toolkit import (
    h, request, get_action, abort, _, ObjectNotFound, NotAuthorized,
    ValidationError,
)
from ckan.plugins import PluginImplementations
try:
    from ckan.plugins import IFormRedirect
except ImportError:
    IFormRedirect = None

from ckan.views.dataset import CreateView, EditView

# FIXME these not available from toolkit
from ckan.lib.navl.dictization_functions import unflatten, DataError
from ckan.logic import clean_dict, tuplize_dict, parse_params


def _clean_page(package_type, page):
    '''return int page or raise ValueError if invalid for package_type'''
    page = int(page)
    if page < 1 or len(h.scheming_get_dataset_form_pages(package_type)) < page:
        raise ValueError('page number out of range')
    return page


class SchemingCreateView(CreateView):
    '''
    View for creating datasets with form pages
    '''
    def post(self, package_type):
        rval = super(SchemingCreateView, self).post(package_type)
        if getattr(rval, 'status_code', None) == 302:
            # successful create on DRUF page 1; send to new resource page
            return h.redirect_to('{}_resource.new'.format(package_type), id=request.form['name'],)
        return rval


class SchemingCreatePageView(CreateView):
    '''
    Handle dataset form pages using package_patch
    '''
    def get(self, package_type, id):
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        data['_form_page'] = 1
        return super(SchemingCreatePageView, self).get(package_type, data)

    def post(self, package_type, id):
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        # BEGIN: roughly copied from ckan/views/dataset.py
        try:
            data_dict = clean_dict(
                unflatten(tuplize_dict(parse_params(request.form)))
            )
        except DataError:
            return abort(400, _(u'Integrity Error'))
        save_action = data_dict.pop('save', None)
        data_dict.pop('pkg_name', None)
        data_dict['state'] = 'draft'
        # END: roughly copied from ckan/views/dataset.py

        data_dict['id'] = id
        try:
            complete_data = get_action('package_patch')(None, data_dict)
        except ObjectNotFound:
            return abort(404, _('Dataset not found'))
        except NotAuthorized:
            return abort(403, _(u'Unauthorized to update a dataset'))
        except ValidationError as e:
            # BEGIN: roughly copied from ckan/views/dataset.py
            errors = e.error_dict
            error_summary = e.error_summary
            data_dict[u'state'] = data[u'state']
            data_dict['_form_page'] = 1

            return EditView().get(
                package_type,
                id,
                data_dict,
                errors,
                error_summary
            )
            # END: roughly copied from ckan/views/dataset.py

        return h.redirect_to(
            '{}.scheming_edit_page'.format(package_type),
            id=complete_data['name'],
            page=2,
        )


def edit(package_type, id):
    if h.scheming_get_dataset_form_pages(package_type):
        return h.redirect_to(
            '{}.scheming_edit_page'.format(package_type),
            id=id,
            page=1
        )
    return EditView().get(package_type, id)


class SchemingEditPageView(EditView):
    '''
    Handle dataset form pages using package_patch
    '''
    def get(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        return super(SchemingEditPageView, self).get(package_type, id, {'_form_page':page})

    def post(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        # BEGIN: roughly copied from ckan/views/dataset.py
        try:
            data_dict = clean_dict(
                unflatten(tuplize_dict(parse_params(request.form)))
            )
        except DataError:
            return abort(400, _(u'Integrity Error'))

        try:
            data_dict.pop('_ckan_phase', None)
            data_dict.pop('save', None)
            data_dict['id'] = id
            # END: roughly copied from ckan/views/dataset.py
            save_action = 'save'
            if page == len(h.scheming_get_dataset_form_pages(package_type)):
                data_dict['state'] = 'active'
            complete_data = get_action('package_patch')(
                {'allow_state_change': True}, data_dict)

            if page < len(h.scheming_get_dataset_form_pages(package_type)):
                if page == 1:
                    # Redirect to 'add data' page
                    url = h.url_for('{}_resource.new'.format(package_type), id=id)
                else:
                    # Redirect to next DRUF page
                    url = h.url_for(
                        f'{package_type}.scheming_edit_page', id=id,
                        page=page + 1)
                return h.redirect_to(url)

            # BEGIN: roughly copied from ckan/views/dataset.py
            for plugin in PluginImplementations(IFormRedirect):
                url = plugin.dataset_save_redirect(
                    package_type, complete_data['name'], 'edit', save_action,
                    complete_data)
                if url:
                    return h.redirect_to(url)

            url = h.url_for('{0}.read'.format(package_type), id=id)
            return h.redirect_to(url)

        except NotAuthorized:
            return abort(403, _(u'Unauthorized to update a dataset'))
        except ObjectNotFound:
            return abort(404, _('Dataset not found'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            data_dict[u'state'] = data[u'state']
            data_dict['_form_page'] = page

            return EditView().get(
                package_type,
                id,
                data_dict,
                errors,
                error_summary
            )
        # END: roughly copied from ckan/views/dataset.py

from flask import Response, Blueprint
from flask.views import MethodView
from werkzeug.datastructures import MultiDict

from ckan.plugins.toolkit import (
    h, request, get_action, abort, _, ObjectNotFound, NotAuthorized,
    ValidationError,
)
from ckan.plugins import PluginImplementations
try:
    from ckan.plugins import IFormRedirect
except ImportError:
    IFormRedirect = None

from ckan.views.dataset import CreateView, EditView

# FIXME these not available from toolkit
from ckan.lib.navl.dictization_functions import unflatten, DataError
from ckan.logic import clean_dict, tuplize_dict, parse_params
import socket
from ckan.plugins import toolkit as tk
import logging
from ckan.plugins.toolkit import config, render
from ckan.common import config as common_config
from datetime import datetime

log = logging.getLogger(__name__)


def _clean_page(package_type, page):
    '''return int page or raise ValueError if invalid for package_type'''
    page = int(page)
    if page < 1 or len(h.scheming_get_dataset_form_pages(package_type)) < page:
        raise ValueError('page number out of range')
    return page

def generate_dataset_approval_email(dataset: dict) -> str:
    
    site_title = common_config.get("ckan.site_title", "CKAN Instance")
    editor_url = f"{common_config.get('ckan.site_url')}/dataset/edit/{dataset['id']}"
    api_url = f"{common_config.get('ckan.site_url')}/api/3/action/package_show?id={dataset['id']}"
    report_url = f"{common_config.get('ckan.site_url')}/ckan-admin/approval-report"

    extra_vars = {
        "dataset_title": dataset.get("title"),
        "dataset_notes": dataset.get("notes", ""),
        "editor_url": editor_url,
        "api_url": api_url,
        "site_title": site_title,
        "report_url": report_url
    }

    return render("emails/email_sysadmin.html", extra_vars)

def generate_dataset_approval_email_txt(dataset: dict) -> str:
    
    site_title = common_config.get("ckan.site_title", "CKAN Instance")
    editor_url = f"{common_config.get('ckan.site_url')}/dataset/edit/{dataset['id']}"
    api_url = f"{common_config.get('ckan.site_url')}/api/3/action/package_show?id={dataset['id']}"
    report_url = f"{common_config.get('ckan.site_url')}/ckan-admin/approval-report"

    extra_vars = {
        "dataset_title": dataset.get("title"),
        "dataset_notes": dataset.get("notes", ""),
        "editor_url": editor_url,
        "api_url": api_url,
        "site_title": site_title,
        "report_url": report_url
    }
    return render('emails/email_sysadmin.txt', extra_vars)


def send_admin_email(email_template_txt: str, email_template_html: str) -> None:
    """
    Send the email to the administrators.
    """
    log.info("Trying to send an email to TWDH administrator")
    # emails = h.sysadmin_emails()

    try:
        admin_name = tk.config.get("ckanext.twdh.admin_name", "TWDH Administrator")
        admin_email = "dipak.shetty@twdb.texas.gov" #tk.config.get("ckanext.contact.mail_to","DataHub@twdh.texas.gov")
        subject = "Data Resource Ready for Review " #tk.config.get("ckanext.twdh.admin_email_subject","Dataset Approval Request")
        tk.mail_recipient(admin_name, admin_email, subject, email_template_txt, email_template_html)

        # Don't send to all sysadmins for now
        '''
        for email in emails:
            log.info(f"Sending email to {email}")
            tk.mail_recipient("Admin", email,
                              subject, email_template_txt, email_template_html)
        '''

    except (Exception, socket.error):
        log.error("Error sending an email to administators")
        return
    log.info("Email succesfully sent to administrators")

def send_editor_submission_confirmation(user_email: str, user_name: str, dataset_title: str, dataset_url: str):
    
    log.info(f"Sending submission confirmation to Editor: {user_email}")
    try:
        subject = "Texas Water Data Hub Submission Confirmation"
        extra_vars = {
            "user_name": user_name,
            "dataset_title": dataset_title,
            "dataset_url": dataset_url,
            "site_title": tk.config.get('ckan.site_title'),
            "site_url": tk.config.get('ckan.site_url')
        }

        body = tk.render("emails/editor_submitted.txt", extra_vars)
        body_html = tk.render("emails/editor_submitted.html", extra_vars)

        tk.mail_recipient(user_name, user_email, subject, body, body_html)
        log.info("Confirmation email sent to Editor successfully.")
    except Exception as e:
        log.error(f"Failed to send confirmation email to Editor: {e}")

def send_editor_approval_notification(user_email: str, user_name: str, dataset_title: str, dataset_url: str):
    
    log.info(f"Sending approval notification to Editor: {user_email}")
    try:
        subject = "Your Data Resource is Published!"
        extra_vars = {
            "user_name": user_name,
            "dataset_title": dataset_title,
            "dataset_url": dataset_url,
            "site_title": tk.config.get('ckan.site_title'),
            "site_url": tk.config.get('ckan.site_url')
        }

        body = tk.render("emails/editor_approved.txt", extra_vars)
        body_html = tk.render("emails/editor_approved.html", extra_vars)

        tk.mail_recipient(user_name, user_email, subject, body, body_html)
        log.info("Approval notification sent to Editor successfully.")
    except Exception as e:
        log.error(f"Failed to send approval notification to Editor: {e}")


class SchemingCreateView(CreateView):
    '''
    View for creating datasets with form pages
    '''
    def post(self, package_type):
        rval = super(SchemingCreateView, self).post(package_type)
        if getattr(rval, 'status_code', None) == 302:
            # successful create on DRUF page 1; send to new resource page
            return h.redirect_to('{}_resource.new'.format(package_type), id=request.form['name'],)
        return rval


class SchemingCreatePageView(CreateView):
    '''
    Handle dataset form pages using package_patch
    '''
    def get(self, package_type, id):
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        data['_form_page'] = 1
        return super(SchemingCreatePageView, self).get(package_type, data)

    def post(self, package_type, id):
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        # BEGIN: roughly copied from ckan/views/dataset.py
        try:
            data_dict = clean_dict(
                unflatten(tuplize_dict(parse_params(request.form)))
            )
        except DataError:
            return abort(400, _(u'Integrity Error'))
        save_action = data_dict.pop('save', None)
        data_dict.pop('pkg_name', None)
        data_dict['state'] = 'draft'
        # END: roughly copied from ckan/views/dataset.py

        data_dict['id'] = id
        try:
            complete_data = get_action('package_patch')(None, data_dict)
        except ObjectNotFound:
            return abort(404, _('Dataset not found'))
        except NotAuthorized:
            return abort(403, _(u'Unauthorized to update a dataset'))
        except ValidationError as e:
            # BEGIN: roughly copied from ckan/views/dataset.py
            errors = e.error_dict
            error_summary = e.error_summary
            data_dict[u'state'] = data[u'state']
            data_dict['_form_page'] = 1

            return EditView().get(
                package_type,
                id,
                data_dict,
                errors,
                error_summary
            )
            # END: roughly copied from ckan/views/dataset.py

        return h.redirect_to(
            '{}.scheming_edit_page'.format(package_type),
            id=complete_data['name'],
            page=2,
        )


def edit(package_type, id):
    if h.scheming_get_dataset_form_pages(package_type):
        return h.redirect_to(
            '{}.scheming_edit_page'.format(package_type),
            id=id,
            page=1
        )
    return EditView().get(package_type, id)


class SchemingEditPageView(EditView):
    '''
    Handle dataset form pages using package_patch
    '''
    def get(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        return super(SchemingEditPageView, self).get(package_type, id, {'_form_page':page})

    def post(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        # BEGIN: roughly copied from ckan/views/dataset.py
        try:
            data_dict = clean_dict(
                unflatten(tuplize_dict(parse_params(request.form)))
            )
        except DataError:
            return abort(400, _(u'Integrity Error'))

        try:
            data_dict.pop('_ckan_phase', None)
            # data_dict.pop('save', None)
            data_dict['id'] = id
            # END: roughly copied from ckan/views/dataset.py
            save_action = data_dict.pop('save', 'next')

            pages = h.scheming_get_dataset_form_pages(package_type)
            total_pages = len(pages)

            if page == len(h.scheming_get_dataset_form_pages(package_type)):
                data_dict['state'] = 'active'

            try:
                complete_data = get_action('package_patch')({'allow_state_change': True}, data_dict)
            except ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary
                data_dict['_form_page'] = page
                return EditView().get(package_type, id, data_dict, errors, error_summary)
        
            if save_action == 'previous':
                if page == 2 and data.get('state','draft') == 'draft':
                    return h.redirect_to('{}_resource.new'.format(package_type), id=data_dict['pkg_name']) 
                elif page > 1:
                    return h.redirect_to(f'{package_type}.scheming_edit_page', id=id, page=page - 1)

            elif save_action == 'next':
                if page == 1 and data.get('state','draft') == 'draft':
                    return h.redirect_to('{}_resource.new'.format(package_type), id=data_dict['pkg_name']) 
                elif page < total_pages:
                    return h.redirect_to(f'{package_type}.scheming_edit_page', id=id, page=page + 1)

            elif save_action == 'exit':
                return h.redirect_to(f'{package_type}.read', id=id)
            
            elif save_action == 'update':
                    return h.redirect_to(f'{package_type}.scheming_edit_page', id=id, page=page)
            
            elif save_action == 'approve':
                data_dict['data_admin_approved'] = 'approved'
                data_dict['private'] = False
                data_dict['state'] = 'active'
                try:
                    complete_data = get_action('package_patch')({'allow_state_change': True}, data_dict)
                except ValidationError as e:
                    errors = e.error_dict
                    error_summary = e.error_summary
                    data_dict['_form_page'] = page
                    return EditView().get(package_type, id, data_dict, errors, error_summary)
                
                # Send mail to editor
                try:
                    creator_id = complete_data.get('creator_user_id')
                    if creator_id:
                        creator = tk.get_action('user_show')({}, {'id': creator_id})
                        editor_name = creator.get('fullname') or creator.get('display_name') or creator.get('name', '')
                        editor_email = creator.get('email', '')
                        dataset_url = f"{tk.config.get('ckan.site_url')}/dataset/{complete_data['name']}"
                        send_editor_approval_notification(
                            user_email=editor_email,
                            user_name=editor_name,
                            dataset_title=complete_data.get('title', ''),
                            dataset_url=dataset_url
                        )
                except Exception as e:
                    log.warning(f"Could not send approval notification to Editor: {e}")

                return h.redirect_to(f'{package_type}.read', id=id)
            
            elif save_action == 'unapprove':
                data_dict['data_admin_approved'] = 'unapproved'
                try:
                    complete_data = get_action('package_patch')({'allow_state_change': True}, data_dict)
                except ValidationError as e:
                    errors = e.error_dict
                    error_summary = e.error_summary
                    data_dict['_form_page'] = page
                    return EditView().get(package_type, id, data_dict, errors, error_summary)
                return h.redirect_to(f'{package_type}.read', id=id)
            
            elif save_action == 'publish':
                data_dict['private'] = False
                try:
                    complete_data = get_action('package_patch')({'allow_state_change': True}, data_dict)
                except ValidationError as e:
                    errors = e.error_dict
                    error_summary = e.error_summary
                    data_dict['_form_page'] = page
                    return EditView().get(package_type, id, data_dict, errors, error_summary)
                return h.redirect_to(f'{package_type}.read', id=id)

            elif save_action in ['submit_for_approval']:
                data_dict['state'] = 'active'
                try:
                    complete_data = get_action('package_patch')({'allow_state_change': True}, data_dict)
                except ValidationError as e:
                    errors = e.error_dict
                    error_summary = e.error_summary
                    data_dict['_form_page'] = page
                    return EditView().get(package_type, id, data_dict, errors, error_summary)
                
                #Editor Detail
                editor_name = ''
                editor_email = ''
                try:
                    creator_id = complete_data.get('creator_user_id')
                    if creator_id:
                        creator = tk.get_action('user_show')({}, {'id': creator_id})
                        editor_name = creator.get('fullname') or creator.get('display_name') or creator.get('name', '')
                        editor_email = creator.get('email', '')
                except Exception as e:
                    log.warning(f"Could not resolve creator user: {e}")

                # Organization title
                organization_title = ''
                try:
                    org_obj = complete_data.get('organization')
                    if isinstance(org_obj, dict):
                        organization_title = org_obj.get('title') or org_obj.get('name') or ''
                    elif complete_data.get('owner_org'):
                        org = tk.get_action('organization_show')({}, {'id': complete_data['owner_org']})
                        organization_title = org.get('title') or org.get('name') or ''
                except Exception as e:
                    log.warning(f"Could not resolve organization: {e}")

                # Date submitted (UTC)
                date_submitted = datetime.utcnow().strftime('%Y-%m-%d')

                # First resource download URL (if any)
                download_url = ''
                try:
                    for r in (complete_data.get('resources') or []):
                        if r.get('url'):
                            download_url = r['url']
                            break
                except Exception:
                    pass

                # Links
                site_url = tk.config.get('ckan.site_url', '')
                editor_url = f"{site_url}/dataset/edit/{complete_data['id']}"
                api_url = f"{site_url}/api/3/action/package_show?id={complete_data['id']}"
                report_url = f"{site_url}/ckan-admin/approval-report"

                extra_vars = {
                    "dataset_title": complete_data.get("title"),
                    "dataset_notes": complete_data.get("notes", ""),
                    "editor_name": editor_name,
                    "editor_email": editor_email,
                    "organization_title": organization_title,
                    "date_submitted": date_submitted,
                    "editor_url": editor_url,
                    "download_url": download_url or "N/A",
                    "api_url": api_url,
                    "report_url": report_url,
                    "site_title": tk.config.get("ckan.site_title"),
                }

                log.info(extra_vars)
                # Render + send to SysAdmin (uses your existing templates under templates/emails/)
                email_html = render("emails/email_sysadmin.html", extra_vars)
                email_txt = render("emails/email_sysadmin.txt", extra_vars)
                    
                # email_html = generate_dataset_approval_email(data)
                # email_txt = generate_dataset_approval_email_txt(data)
                send_admin_email(email_txt,email_html)

                 # Optional: confirmation back to the Editor who submitted
                try:
                    if editor_email:
                        subj_url = f"{site_url}/dataset/edit/{complete_data['name']}"
                        send_editor_submission_confirmation(
                            user_email=editor_email,
                            user_name=editor_name or "Editor",
                            dataset_title=complete_data.get('title', ''),
                            dataset_url=subj_url
                        )
                except Exception as e:
                    log.warning(f"Could not send editor confirmation email: {e}")

#                 send_editor_submission_confirmation(
#                     user_email=user_obj.email,
#                     user_name=user_obj.display_name or user_obj.name,
#                     dataset_title=dataset['title'],
#                     dataset_url=h.url_for('dataset.edit', id=dataset['name'], qualified=True)
# )
                return h.redirect_to(f'{package_type}.read', id=id)

            if page < len(h.scheming_get_dataset_form_pages(package_type)):
                if page == 1:
                    # Redirect to 'add data' page
                    url = h.url_for('{}_resource.new'.format(package_type), id=id)
                else:
                    # Redirect to next DRUF page
                    url = h.url_for(
                        f'{package_type}.scheming_edit_page', id=id,
                        page=page + 1)
                return h.redirect_to(url)

            # BEGIN: roughly copied from ckan/views/dataset.py
            for plugin in PluginImplementations(IFormRedirect):
                url = plugin.dataset_save_redirect(
                    package_type, complete_data['name'], 'edit', save_action,
                    complete_data)
                if url:
                    return h.redirect_to(url)

            url = h.url_for('{0}.read'.format(package_type), id=id)
            return h.redirect_to(url)

        except NotAuthorized:
            return abort(403, _(u'Unauthorized to update a dataset'))
        except ObjectNotFound:
            return abort(404, _('Dataset not found'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            data_dict[u'state'] = data[u'state']
            data_dict['_form_page'] = page

            return EditView().get(
                package_type,
                id,
                data_dict,
                errors,
                error_summary
            )
        # END: roughly copied from ckan/views/dataset.py
