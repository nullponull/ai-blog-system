#!/usr/bin/env python3
"""
GitHub Actionsワークフローに記事補完機能を統合するための設定
"""

import yaml
import os
from pathlib import Path

def create_completion_workflow():
    """
    記事補完専用のGitHub Actionsワークフローを作成
    """
    workflow = {
        'name': 'Article Completion Pipeline',
        'on': {
            'workflow_dispatch': None,
            'schedule': [
                {'cron': '0 9 * * *'}  # 毎日午前9時に実行
            ]
        },
        'jobs': {
            'complete-articles': {
                'runs-on': 'ubuntu-latest',
                'permissions': {
                    'contents': 'write',
                    'pages': 'write',
                    'id-token': 'write'
                },
                'steps': [
                    {
                        'name': 'Checkout repository',
                        'uses': 'actions/checkout@v4',
                        'with': {
                            'fetch-depth': 0
                        }
                    },
                    {
                        'name': 'Setup Python',
                        'uses': 'actions/setup-python@v4',
                        'with': {
                            'python-version': '3.10'
                        }
                    },
                    {
                        'name': 'Install dependencies',
                        'run': 'pip install requests\nmkdir -p _temp scripts'
                    },
                    {
                        'name': 'Check for incomplete articles',
                        'run': '''echo "🔍 Checking for incomplete articles..."
python3 scripts/article_completion_checker.py _posts

if [ -f "_temp/incomplete_articles.txt" ] && [ -s "_temp/incomplete_articles.txt" ]; then
  echo "📋 Found incomplete articles:"
  cat _temp/incomplete_articles.txt
  echo "INCOMPLETE_FOUND=true" >> $GITHUB_ENV
else
  echo "✅ No incomplete articles found"
  echo "INCOMPLETE_FOUND=false" >> $GITHUB_ENV
fi'''
                    },
                    {
                        'name': 'Complete articles',
                        'if': 'env.INCOMPLETE_FOUND == \'true\'',
                        'env': {
                            'GEMINI_API_KEY': '${{ secrets.GEMINI_API_KEY2 }}'
                        },
                        'run': '''echo "🚀 Starting article completion..."
export GEMINI_API_KEY="$GEMINI_API_KEY"

if [ -z "$GEMINI_API_KEY" ]; then
  echo "❌ GEMINI_API_KEY2 is not set"
  exit 1
fi

python3 scripts/article_completer.py

echo "✅ Article completion process finished"'''
                    },
                    {
                        'name': 'Validate completed articles',
                        'if': 'env.INCOMPLETE_FOUND == \'true\'',
                        'run': '''echo "🔍 Re-checking completed articles..."
python3 scripts/article_completion_checker.py _posts

if [ -f "_temp/incomplete_articles.txt" ] && [ -s "_temp/incomplete_articles.txt" ]; then
  echo "⚠️ Some articles still incomplete:"
  cat _temp/incomplete_articles.txt
  echo "COMPLETION_SUCCESS=partial" >> $GITHUB_ENV
else
  echo "✅ All articles completed successfully"
  echo "COMPLETION_SUCCESS=full" >> $GITHUB_ENV
fi'''
                    },
                    {
                        'name': 'Commit completed articles',
                        'if': 'env.INCOMPLETE_FOUND == \'true\'',
                        'run': '''git config --global user.name "github-actions[bot]"
git config --global user.email "github-actions[bot]@users.noreply.github.com"

if [ -n "$(git status --porcelain _posts/)" ]; then
  COMPLETED_COUNT=$(git status --porcelain _posts/ | wc -l)
  git add _posts/
  git commit -m "🔧 Complete $COMPLETED_COUNT articles - $(date +%Y-%m-%d)"
  
  if git push; then
    echo "✅ Successfully pushed completed articles"
  else
    echo "❌ Push failed, attempting force push with lease..."
    git push --force-with-lease || exit 1
  fi
else
  echo "ℹ️ No changes to commit"
fi'''
                    }
                ]
            }
        }
    }
    
    return workflow

def update_main_workflow():
    """
    メインのワークフローに記事補完ステップを追加
    """
    workflow_path = '.github/workflows/improved-ai-pipeline.yml'
    
    if not os.path.exists(workflow_path):
        print(f"❌ メインワークフローファイルが見つかりません: {workflow_path}")
        return False
    
    # 記事補完ステップを挿入するための設定
    completion_step = {
        'name': 'Check and complete incomplete articles',
        'run': '''echo "🔍 Checking for incomplete articles..."
python3 scripts/article_completion_checker.py _posts

if [ -f "_temp/incomplete_articles.txt" ] && [ -s "_temp/incomplete_articles.txt" ]; then
  echo "📋 Found incomplete articles, attempting completion..."
  python3 scripts/article_completer.py
  
  # Re-check after completion
  python3 scripts/article_completion_checker.py _posts
  
  if [ -f "_temp/incomplete_articles.txt" ] && [ -s "_temp/incomplete_articles.txt" ]; then
    echo "⚠️ Some articles still incomplete after completion attempt"
  else
    echo "✅ All articles completed successfully"
  fi
else
  echo "✅ No incomplete articles found"
fi''',
        'env': {
            'GEMINI_API_KEY': '${{ secrets.GEMINI_API_KEY2 }}'
        }
    }
    
    print("💡 メインワークフローファイルの手動更新が必要です")
    print("以下のステップを 'Advanced quality enhancement' の前に追加してください：")
    print("\n" + yaml.dump({'step': completion_step}, default_flow_style=False, allow_unicode=True))
    
    return True

def main():
    """メイン処理"""
    print("🚀 記事補完システムのワークフロー統合を開始...")
    
    # 1. 専用のワークフローファイル作成
    print("\n📝 記事補完専用ワークフローを作成中...")
    completion_workflow = create_completion_workflow()
    
    workflow_dir = Path('.github/workflows')
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    completion_workflow_path = workflow_dir / 'article-completion.yml'
    
    with open(completion_workflow_path, 'w', encoding='utf-8') as f:
        yaml.dump(completion_workflow, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"✅ 記事補完ワークフローを作成: {completion_workflow_path}")
    
    # 2. メインワークフローの更新提案
    print("\n🔄 メインワークフローの更新提案...")
    update_main_workflow()
    
    # 3. 使用方法の説明
    print("\n📖 使用方法:")
    print("1. 自動実行: 毎日午前9時に自動で不完全な記事をチェック・補完")
    print("2. 手動実行: GitHub ActionsページでArticle Completion Pipelineを手動実行")
    print("3. 統合実行: メインのAI記事生成パイプラインに補完機能が組み込まれます")
    
    print("\n⚠️  注意事項:")
    print("- GEMINI_API_KEY2 シークレットが設定されている必要があります")
    print("- 大量の記事補完時はAPI制限に注意してください")
    print("- 補完前の記事は自動でバックアップされます")
    
    print("\n🎉 記事補完システムの統合準備が完了しました！")

if __name__ == "__main__":
    main()