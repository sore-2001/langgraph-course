"""
增量知识图谱构建入口脚本

使用说明:
    # 1. 首次全量构建
    python run_incremental.py --init --pdf-dir ./data/chuankou_pdf

    # 2. 增量更新 (自动检测新增/修改的文档)
    python run_incremental.py --update

    # 3. 添加指定文档
    python run_incremental.py --add file1.pdf file2.pdf

    # 4. 查看已处理文档列表
    python run_incremental.py --list

    # 5. 重建 GraphRAG 社区结构
    python run_incremental.py --rebuild-communities
"""
import sys
import argparse
from pathlib import Path

# 设置 UTF-8 编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 确保项目根目录在搜索路径中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_process.config import Config
from data_process.incremental_builder import IncrementalGraphBuilder
from data_process.utils import logger


def cmd_init(args):
    """首次全量构建知识图谱"""
    builder = IncrementalGraphBuilder()
    stats = builder.build_initial(pdf_dir=args.pdf_dir)
    print(f"\n全量构建完成：{stats}")
    return stats


def cmd_update(args):
    """增量更新知识图谱"""
    builder = IncrementalGraphBuilder()
    stats = builder.incremental_update(
        pdf_dir=args.pdf_dir,
        rebuild_communities=args.rebuild_communities
    )
    print(f"\n增量更新完成：{stats}")
    return stats


def cmd_add(args):
    """添加指定文档"""
    builder = IncrementalGraphBuilder()
    stats = builder.add_documents(args.files)
    print(f"\n添加完成：{stats}")
    return stats


def cmd_list(args):
    """查看已处理文档列表"""
    builder = IncrementalGraphBuilder()
    info = builder.get_registry_info()

    print(f"\n已追踪文档：{info['total_documents']} 个\n")
    print(f"{'文件名':<50} {'文本块':>8} {'三元组':>10} {'处理时间':<25}")
    print("-" * 95)

    for doc in info['documents']:
        print(f"{doc['file']:<50} {doc['chunks']:>8} {doc['triples']:>10} {doc['processed_at'][:19]:<25}")

    print()


def cmd_rebuild_communities(args):
    """重建 GraphRAG 社区结构"""
    builder = IncrementalGraphBuilder()
    builder.rebuild_communities()
    print("\n社区结构重建完成")


def main():
    parser = argparse.ArgumentParser(
        description="增量知识图谱构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_incremental.py --init --pdf-dir ./data/chuankou_pdf  # 首次全量构建
  python run_incremental.py --update                        # 增量更新
  python run_incremental.py --add file1.pdf file2.pdf       # 添加指定文档
  python run_incremental.py --list                          # 查看已处理文档
  python run_incremental.py --rebuild-communities           # 重建社区结构
        """
    )

    # 互斥操作
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--init',
        action='store_true',
        help='首次全量构建知识图谱'
    )
    group.add_argument(
        '--update',
        action='store_true',
        help='增量更新知识图谱 (自动检测新增/修改文档)'
    )
    group.add_argument(
        '--add',
        nargs='+',
        metavar='FILE',
        help='添加指定的 PDF 文档到知识图谱'
    )
    group.add_argument(
        '--list',
        action='store_true',
        help='查看已处理文档列表'
    )
    group.add_argument(
        '--rebuild-communities',
        action='store_true',
        help='重建 GraphRAG 社区结构'
    )

    # 公共参数
    parser.add_argument(
        '--pdf-dir',
        type=str,
        default=Config.PDF_DIR,
        help=f'PDF 目录 (默认：{Config.PDF_DIR})'
    )

    args = parser.parse_args()

    try:
        if args.init:
            cmd_init(args)
        elif args.update:
            cmd_update(args)
        elif args.add:
            cmd_add(args)
        elif args.list:
            cmd_list(args)
        elif args.rebuild_communities:
            cmd_rebuild_communities(args)

        logger.info("操作完成")

    except Exception as e:
        logger.error(f"操作失败：{str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
