import argparse
import os
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image


class ImageProcessor:
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff']

    def validate_input(self, image_path, width, height):
        """验证输入参数"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")

        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"不支持的文件格式。支持格式: {', '.join(self.supported_formats)}")

        if width <= 0 or height <= 0:
            raise ValueError("宽度和高度必须大于0")

        return True

    def get_image_info(self, image_path):
        """获取图片信息"""
        with Image.open(image_path) as img:
            return {
                'format': img.format,
                'size': img.size,
                'mode': img.mode,
                'file_size': os.path.getsize(image_path)
            }

    def resize_with_crop(self, img, target_width, target_height):
        """裁剪模式：裁剪图片中心区域"""
        # 计算缩放比例
        width_ratio = target_width / img.width
        height_ratio = target_height / img.height
        scale_ratio = max(width_ratio, height_ratio)

        # 先缩放
        new_size = (int(img.width * scale_ratio), int(img.height * scale_ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        # 计算裁剪区域
        left = (img.width - target_width) // 2
        top = (img.height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        # 裁剪
        img = img.crop((left, top, right, bottom))
        return img

    def resize_with_compress(self, img, target_width, target_height):
        """压缩模式：等比例缩放，可能会留白"""
        # 计算缩放比例，保持宽高比
        width_ratio = target_width / img.width
        height_ratio = target_height / img.height
        scale_ratio = min(width_ratio, height_ratio)

        # 缩放
        new_size = (int(img.width * scale_ratio), int(img.height * scale_ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        # 创建新图片并粘贴（留白）
        if img.mode == 'RGBA':
            new_img = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 0))
        else:
            new_img = Image.new('RGB', (target_width, target_height), (255, 255, 255))

        # 计算粘贴位置
        paste_x = (target_width - img.width) // 2
        paste_y = (target_height - img.height) // 2
        new_img.paste(img, (paste_x, paste_y))

        return new_img

    def resize_fit(self, img, target_width, target_height):
        """适应模式：直接调整到指定尺寸（可能变形）"""
        return img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    def compress_to_target_size(self, img, target_size_kb, quality=85, step=5):
        """压缩到指定文件大小（仅限JPEG）"""
        if target_size_kb is None:
            return img, quality

        buffer = BytesIO()
        current_quality = quality

        while current_quality > 5:
            buffer.seek(0)
            buffer.truncate(0)

            # 保存到内存缓冲区
            if img.mode == 'RGBA':
                img.convert('RGB').save(buffer, format='JPEG', quality=current_quality, optimize=True)
            else:
                img.save(buffer, format='JPEG', quality=current_quality, optimize=True)

            # 检查文件大小
            size_kb = len(buffer.getvalue()) / 1024

            if size_kb <= target_size_kb:
                break

            # 降低质量
            current_quality -= step

        # 从缓冲区重新加载图片
        buffer.seek(0)
        img = Image.open(buffer)

        return img, current_quality

    def process_image(self, image_path, width, height, mode='crop',
                      target_size_kb=None, output_path=None,
                      quality=85, preserve_metadata=False):
        """
        处理图片的主函数

        参数:
        - image_path: 输入图片路径
        - width: 目标宽度
        - height: 目标高度
        - mode: 'crop' (裁剪), 'compress' (压缩留白), 'fit' (直接调整)
        - target_size_kb: 目标文件大小（KB），None表示不限制
        - output_path: 输出路径，None则自动生成
        - quality: 图片质量 (1-100)
        - preserve_metadata: 是否保留元数据
        """

        # 验证输入
        self.validate_input(image_path, width, height)

        # 获取原始图片信息
        original_info = self.get_image_info(image_path)
        print(f"原始图片信息:")
        print(f"  尺寸: {original_info['size'][0]}x{original_info['size'][1]}")
        print(f"  格式: {original_info['format']}")
        print(f"  大小: {original_info['file_size'] / 1024:.2f} KB")

        # 打开图片
        with Image.open(image_path) as img:
            # 转换为RGB（如果带透明度）
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P' and 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')

            # 保留元数据
            if preserve_metadata:
                exif = img.info.get('exif')

            # 根据模式处理
            if mode == 'crop':
                img = self.resize_with_crop(img, width, height)
            elif mode == 'compress':
                img = self.resize_with_compress(img, width, height)
            elif mode == 'fit':
                img = self.resize_fit(img, width, height)
            else:
                raise ValueError(f"不支持的模式: {mode}")

            print(f"处理后尺寸: {img.width}x{img.height}")

            # 如果需要压缩到指定大小
            if target_size_kb is not None:
                img, final_quality = self.compress_to_target_size(img, target_size_kb, quality)
                print(f"压缩质量: {final_quality}")
            else:
                final_quality = quality

            # 生成输出路径
            if output_path is None:
                path_obj = Path(image_path)
                suffix = path_obj.suffix.lower()
                if suffix == '.jpeg' or suffix == '.jpg':
                    output_suffix = '.jpg'
                elif suffix == '.png':
                    output_suffix = '.png'
                else:
                    output_suffix = '.jpg'  # 默认保存为JPEG

                output_path = str(path_obj.parent / f"{path_obj.stem}_processed{output_suffix}")

            # 保存图片
            save_kwargs = {
                'optimize': True,
                'quality': final_quality
            }

            if preserve_metadata and 'exif' in locals() and exif:
                save_kwargs['exif'] = exif

            # 根据格式保存
            output_ext = os.path.splitext(output_path)[1].lower()
            if output_ext in ['.jpg', '.jpeg']:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(output_path, 'JPEG', **save_kwargs)
            elif output_ext == '.png':
                img.save(output_path, 'PNG', **save_kwargs)
            else:
                # 默认保存为JPEG
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                output_path = output_path.rsplit('.', 1)[0] + '.jpg'
                img.save(output_path, 'JPEG', **save_kwargs)

            # 显示结果信息
            final_info = self.get_image_info(output_path)
            print(f"\n处理完成!")
            print(f"输出文件: {output_path}")
            print(f"最终尺寸: {final_info['size'][0]}x{final_info['size'][1]}")
            print(f"最终大小: {final_info['file_size'] / 1024:.2f} KB")

            if target_size_kb and final_info['file_size'] / 1024 > target_size_kb:
                print(f"警告: 未能压缩到目标大小 {target_size_kb}KB")

            return output_path


def main():
    parser = argparse.ArgumentParser(description='图片处理工具')
    parser.add_argument('image_path', help='输入图片路径')
    parser.add_argument('-w', '--width', type=int, required=True, help='目标宽度')
    parser.add_argument('-H', '--height', type=int, required=True, help='目标高度')
    parser.add_argument('-m', '--mode', choices=['crop', 'compress', 'fit'],
                        default='crop', help='处理模式: crop(裁剪), compress(压缩留白), fit(直接调整)')
    parser.add_argument('-s', '--size', type=float, help='目标文件大小(KB)')
    parser.add_argument('-o', '--output', help='输出路径')
    parser.add_argument('-q', '--quality', type=int, default=85,
                        help='图片质量 (1-100)，默认85')
    parser.add_argument('--preserve-metadata', action='store_true',
                        help='保留EXIF等元数据')

    args = parser.parse_args()

    processor = ImageProcessor()

    try:
        processor.process_image(
            image_path=args.image_path,
            width=args.width,
            height=args.height,
            mode=args.mode,
            target_size_kb=args.size,
            output_path=args.output,
            quality=args.quality,
            preserve_metadata=args.preserve_metadata
        )
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    processor = ImageProcessor()

    # 示例1: 裁剪图片到800x600，不限制大小
    result = processor.process_image(
        image_path=r"C:\Users\sunhouyun\Desktop\zx.jpg",
        width=358*3,
        height=441*3,
        mode='crop',
        target_size_kb=None,
        output_path="output_crop.jpg",
        quality=100
    )

    # 示例2: 压缩图片到400x300，限制文件大小为100KB
    # result = processor.process_image(
    #     image_path="input.jpg",
    #     width=400,
    #     height=300,
    #     mode='compress',
    #     target_size_kb=100,
    #     output_path="output_compressed.jpg"
    # )

    # 示例3: 直接调整图片尺寸（可能变形）
    # result = processor.process_image(
    #     image_path="input.jpg",
    #     width=600,
    #     height=400,
    #     mode='fit',
    #     output_path="output_fit.jpg"
    # )