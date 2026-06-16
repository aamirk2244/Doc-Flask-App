import os
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
import pandas as pd

from services import allowed_file, find_latest_upload, load_dataframe, compare_data, ensure_dirs
from settings import INITIAL_DIR

bp = Blueprint('main', __name__)


def _get_initial_path_and_name():
    initial_path = None
    initial_name = None
    if os.path.isdir(INITIAL_DIR):
        for f in os.listdir(INITIAL_DIR):
            initial_path = os.path.join(INITIAL_DIR, f)
            initial_name = f
            break
    return initial_path, initial_name


@bp.route('/')
def index():
    initial_filename = None
    initial_mtime = None
    initial_path, initial_filename = _get_initial_path_and_name()
    if initial_path:
        try:
            initial_mtime = pd.to_datetime(os.path.getmtime(initial_path), unit='s')
            initial_mtime = pd.to_datetime(os.path.getmtime(initial_path), unit='s')
        except Exception:
            initial_mtime = None

    initial_exists = initial_filename is not None

    # latest comparison file
    latest = find_latest_upload()
    new_filename = os.path.basename(latest) if latest else None
    new_mtime = None
    if latest:
        try:
            new_mtime = pd.to_datetime(os.path.getmtime(latest), unit='s')
        except Exception:
            new_mtime = None

    return render_template('index.html', initial_exists=initial_exists, initial_filename=initial_filename, initial_mtime=initial_mtime, new_exists=bool(latest), new_filename=new_filename, new_mtime=new_mtime)


@bp.route('/view_initial')
def view_initial():
    initial_path, initial_name = _get_initial_path_and_name()
    if not initial_path:
        flash('No initial file uploaded')
        return redirect(url_for('main.index'))
    return send_file(initial_path, as_attachment=True, download_name=initial_name)


@bp.route('/remove_initial', methods=['POST'])
def remove_initial():
    removed = False
    removed_files = []
    if os.path.isdir(INITIAL_DIR):
        for f in os.listdir(INITIAL_DIR):
            try:
                os.remove(os.path.join(INITIAL_DIR, f))
                removed = True
                removed_files.append(f)
            except Exception:
                pass
    if removed:
        flash('Initial reference removed')
        current_app.logger.info('Removed initial files: %s', ','.join(removed_files))
    else:
        flash('No initial reference to remove')
        current_app.logger.info('remove_initial called but no files present')
    return redirect(url_for('main.index'))


@bp.route('/upload_initial', methods=['POST'])
def upload_initial():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('main.index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('main.index'))
    if file and allowed_file(file.filename):
        filename = pd.io.common.get_handle(file.filename, 'r')[0] if False else file.filename
        # preserve original filename, but use the dedicated initial folder
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        # clear existing initial file(s)
        if os.path.isdir(INITIAL_DIR):
            for f in os.listdir(INITIAL_DIR):
                try:
                    os.remove(os.path.join(INITIAL_DIR, f))
                except Exception:
                    pass
        save_path = os.path.join(INITIAL_DIR, filename)
        file.save(save_path)
        flash('Initial file uploaded')
        current_app.logger.info('Uploaded initial file: %s', filename)
        return redirect(url_for('main.index'))
    flash('Invalid file type')
    return redirect(url_for('main.index'))


@bp.route('/upload_new', methods=['POST'])
def upload_new():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('main.index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('main.index'))
    if file and allowed_file(file.filename):
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        flash('Comparison file uploaded')
        current_app.logger.info('Uploaded comparison file: %s', save_path)
        return redirect(url_for('main.compare'))
    flash('Invalid file type')
    return redirect(url_for('main.index'))


@bp.route('/compare', methods=['GET'])
def compare():
    initial_path, _ = _get_initial_path_and_name()
    new_path = find_latest_upload()

    if not initial_path:
        flash('No initial file uploaded. Please upload initial reference file first.')
        return redirect(url_for('main.index'))
    if not new_path:
        flash('No comparison file uploaded. Please upload the file to compare.')
        return redirect(url_for('main.index'))

    try:
        initial_df = load_dataframe(initial_path)
        new_df = load_dataframe(new_path)
        current_app.logger.info('Running comparison: initial=%s new=%s', initial_path, new_path)
        results = compare_data(initial_df, new_df)
        mismatch_count = sum(1 for r in results if r['status'] != 'ok')
        current_app.logger.info('Comparison finished; total_keys=%d mismatches_or_missing=%d', len(results), mismatch_count)
        flash('Comparison completed successfully')
    except Exception as e:
        current_app.logger.exception('Error during comparison')
        flash('Error during comparison: {}'.format(str(e)))
        return redirect(url_for('main.index'))

    rows = []
    for r in results:
        if r['status'] != 'ok':
            if r['status'] == 'missing_in_initial':
                rows.append({'KEY': r['key'], 'status': r['status'], 'column': '', 'initial': '', 'new': ''})
            else:
                for m in r['mismatches']:
                    rows.append({'KEY': r['key'], 'status': r['status'], 'column': m['column'], 'initial': m['initial'], 'new': m['new']})

    csv_buffer = BytesIO()
    if rows:
        pd.DataFrame(rows).to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        csv_ready = True
    else:
        csv_buffer = None
        csv_ready = False

    issues_count = len(rows)

    return render_template('results.html', results=results, csv_ready=csv_ready, issues_count=issues_count)


@bp.route('/download_results')
def download_results():
    initial_path, _ = _get_initial_path_and_name()
    new_path = find_latest_upload()
    if not initial_path or not new_path:
        flash('Missing files for download')
        return redirect(url_for('main.index'))

    initial_df = load_dataframe(initial_path)
    new_df = load_dataframe(new_path)
    current_app.logger.info('Regenerating results for download: initial=%s new=%s', initial_path, new_path)
    results = compare_data(initial_df, new_df)

    rows = []
    for r in results:
        if r['status'] != 'ok':
            if r['status'] == 'missing_in_initial':
                rows.append({'KEY': r['key'], 'status': r['status'], 'column': '', 'initial': '', 'new': ''})
            else:
                for m in r['mismatches']:
                    rows.append({'KEY': r['key'], 'status': r['status'], 'column': m['column'], 'initial': m['initial'], 'new': m['new']})

    buffer = BytesIO()
    pd.DataFrame(rows).to_csv(buffer, index=False)
    buffer.seek(0)
    return send_file(buffer, mimetype='text/csv', as_attachment=True, download_name='comparison_results.csv')


def register_routes(app):
    ensure_dirs()
    app.register_blueprint(bp)
