"""
图纸领域值对象。
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from idmas.domain.shared.exceptions import InvalidDrawingError

# 单边最大像素（与 settings.IMAGE_MAX_DIMENSION 同步，此处作为领域常量）
IMAGE_MAX_DIMENSION = 4096


class DrawingType(str, Enum):
    """图纸类型。"""
    assembly  = "assembly"    # 装配图
    part      = "part"        # 零件图
    process   = "process"     # 工艺图
    schematic = "schematic"   # 原理图/电路图
    patent    = "patent"      # 专利附图
    other     = "other"


class FileFormat(str, Enum):
    """支持的文件格式。"""
    png  = "png"
    jpg  = "jpg"
    pdf  = "pdf"
    dwg  = "dwg"
    dxf  = "dxf"


class LifecycleState(str, Enum):
    """图纸生命周期状态（对接 PLM 状态机）。"""
    draft    = "draft"       # 草稿
    released = "released"    # 已发布
    obsolete = "obsolete"    # 已废弃


# ------------------------------------------------------------------
# BoundingBox
# ------------------------------------------------------------------

class BoundingBox(BaseModel):
    """
    边界框值对象，使用归一化坐标（0.0 ~ 1.0）。
    x, y 为左上角坐标；width, height 为宽高。
    """
    model_config = {"frozen": True}

    x:      Annotated[float, Field(ge=0.0, le=1.0)]
    y:      Annotated[float, Field(ge=0.0, le=1.0)]
    width:  Annotated[float, Field(gt=0.0, le=1.0)]
    height: Annotated[float, Field(gt=0.0, le=1.0)]

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.x + self.width > 1.0 + 1e-6:
            raise ValueError(f"x({self.x}) + width({self.width}) exceeds 1.0")
        if self.y + self.height > 1.0 + 1e-6:
            raise ValueError(f"y({self.y}) + height({self.height}) exceeds 1.0")
        return self

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)


# ------------------------------------------------------------------
# SpatialInfo
# ------------------------------------------------------------------

class Quadrant(str, Enum):
    """图纸象限（左上/右上/左下/右下），用于空间推理。"""
    top_left     = "top_left"
    top_right    = "top_right"
    bottom_left  = "bottom_left"
    bottom_right = "bottom_right"
    center       = "center"


class SpatialInfo(BaseModel):
    """
    标号空间信息值对象。
    position：归一化中心坐标 (cx, cy)。
    """
    model_config = {"frozen": True}

    position: tuple[float, float]   # (cx, cy)，归一化
    quadrant: Quadrant
    region:   str = ""              # 自然语言描述，如"左上方传动轴区域"

    @classmethod
    def from_bounding_box(cls, bbox: BoundingBox, region: str = "") -> "SpatialInfo":
        cx, cy = bbox.center
        if cx < 0.5 and cy < 0.5:
            quadrant = Quadrant.top_left
        elif cx >= 0.5 and cy < 0.5:
            quadrant = Quadrant.top_right
        elif cx < 0.5 and cy >= 0.5:
            quadrant = Quadrant.bottom_left
        else:
            quadrant = Quadrant.bottom_right
        return cls(position=(cx, cy), quadrant=quadrant, region=region)


# ------------------------------------------------------------------
# ImageDimension
# ------------------------------------------------------------------

class ImageDimension(BaseModel):
    """
    图片尺寸值对象。
    校验：单边不超过 IMAGE_MAX_DIMENSION（4096）像素。
    """
    model_config = {"frozen": True}

    width:  Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def validate_dimension(self) -> "ImageDimension":
        if self.width > IMAGE_MAX_DIMENSION or self.height > IMAGE_MAX_DIMENSION:
            raise InvalidDrawingError(
                f"Image dimension {self.width}×{self.height} exceeds "
                f"max allowed {IMAGE_MAX_DIMENSION}px per side"
            )
        return self

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    @property
    def megapixels(self) -> float:
        return (self.width * self.height) / 1_000_000
