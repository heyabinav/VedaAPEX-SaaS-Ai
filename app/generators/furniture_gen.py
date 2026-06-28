import bpy
import argparse
import sys


def main():
    # Parse custom arguments passed after '--'
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--width", type=float, default=1.0)
    parser.add_argument("--depth", type=float, default=1.0)
    parser.add_argument("--height", type=float, default=0.75)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])

    # Clear scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Procedural generation: Simple table
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, args.height))
    table_top = bpy.context.active_object
    table_top.scale = (args.width, args.depth, 0.05)

    # Export
    bpy.ops.export_scene.gltf(filepath=args.output, export_format="GLB")


if __name__ == "__main__":
    main()
