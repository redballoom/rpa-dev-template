import subprocess

import pytest

from tools.delivery_version import delivery_version, is_record_path
from tools.evidence import build_summary, validate_summary


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.invalid')
    (tmp_path / 'runner.py').write_text('baseline\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-m', 'baseline')
    return tmp_path


def test_records_do_not_poison_next_run(repo):
    result = {'status': 'success', 'data': {'run_id': 'one'}}
    first = build_summary(result, repo, None, None, 'start', 'end')
    assert first['run']['working_tree_clean'] is True
    record = repo / 'evidence/runs/one.summary.json'
    record.parent.mkdir(parents=True)
    record.write_text('{}')
    second = build_summary(result, repo, None, None, 'start', 'end')
    assert second['schema_version'] == 2
    assert second['run']['working_tree_clean'] is False
    assert second['run']['delivery_tree_clean'] is True
    assert validate_summary(second)['valid']
    (repo / 'unknown.txt').write_text('unknown')
    assert not build_summary(result, repo, None, None, 'start', 'end')['run']['delivery_tree_clean']


def test_record_commit_compatible_code_commit_not(repo):
    baseline = git(repo, 'rev-parse', 'HEAD')
    record = repo / '.project-gates/gate-history.md'
    record.parent.mkdir()
    record.write_text('record\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'record')
    assert delivery_version(repo, baseline)['baseline_compatible']
    (repo / 'runner.py').write_text('changed\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'code')
    assert not delivery_version(repo, baseline)['baseline_compatible']


def test_staged_edit_and_rename_are_not_hidden(repo):
    (repo / 'runner.py').write_text('staged change\n')
    git(repo, 'add', '.')
    (repo / 'runner.py').write_text('baseline\n')
    assert not delivery_version(repo)['delivery_tree_clean']
    git(repo, 'add', '.')
    git(repo, 'mv', 'runner.py', 'new name.py')
    result = delivery_version(repo)
    assert {'runner.py', 'new name.py'} <= set(result['delivery_paths'])


def test_missing_git_fails_closed(tmp_path):
    assert not delivery_version(tmp_path)['ok']
    assert not delivery_version(tmp_path)['delivery_tree_clean']


@pytest.mark.parametrize('path', ['.trellis/config.yaml', '.trellis/scripts/task.py',
                                 '.trellis/spec/backend/index.md', 'evidence/runs/test.py',
                                 'evidence/runs/nested/test.summary.json', '.agents/skills/a/SKILL.md'])
def test_unknown_or_executable_path_is_delivery(path):
    assert not is_record_path(path)
