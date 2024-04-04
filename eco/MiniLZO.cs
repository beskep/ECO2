using System;
using System.Diagnostics;

namespace MiniLZO
{
    // ECO2_2020V2/Utility/MiniLZO
    public static class MiniLZO
    {
        private const uint m_a = 8u;

        private const uint b = 33u;

        private const uint c = 9u;

        private const byte d = 32;

        private const byte e = 16;

        private const uint f = 1024u;

        private const uint g = 2048u;

        private const uint h = 16384u;

        private const uint i = 49151u;

        private const byte j = 14;

        private const uint k = 16383u;

        private const uint l = 65539u;

        public static unsafe void Compress(byte[] src, out byte[] dst)
        {
            uint num = (uint)(src.Length + src.Length / 16 + 64 + 3);
            dst = new byte[num];
            uint num2;
            if ((long)src.Length <= 13L)
            {
                num2 = (uint)src.Length;
                num = 0u;
            }
            else
            {
                fixed (byte* ptr = new byte[65539])
                {
                    fixed (byte* ptr3 = src)
                    {
                        fixed (byte* ptr8 = dst)
                        {
                            byte** ptr2 = (byte**)ptr;
                            byte* ptr4 = ptr3 + src.Length;
                            byte* ptr5 = ptr3 + src.Length - 8u - 5;
                            byte* ptr6 = ptr3;
                            byte* ptr7 = ptr3 + 4;
                            byte* ptr9 = ptr8;
                            bool flag = false;
                            bool flag2 = false;
                            while (true)
                            {
                                uint num3 = 0u;
                                uint num4 = a(ptr7);
                                byte* ptr10 = ptr7 - (ptr7 - ptr2[num4]);
                                if (
                                    ptr10 < ptr3
                                    || (num3 = (uint)(ptr7 - ptr10)) == 0
                                    || num3 > 49151
                                )
                                {
                                    flag = true;
                                }
                                else if (num3 > 2048 && ptr10[3] != ptr7[3])
                                {
                                    num4 = a(num4);
                                    ptr10 = ptr7 - (ptr7 - ptr2[num4]);
                                    if (
                                        ptr10 < ptr3
                                        || (num3 = (uint)(ptr7 - ptr10)) == 0
                                        || num3 > 49151
                                    )
                                    {
                                        flag = true;
                                    }
                                    else if (num3 > 2048 && ptr10[3] != ptr7[3])
                                    {
                                        flag = true;
                                    }
                                }
                                if (
                                    !flag
                                    && *(ushort*)ptr10 == *(ushort*)ptr7
                                    && ptr10[2] == ptr7[2]
                                )
                                {
                                    flag2 = true;
                                }
                                flag = false;
                                if (!flag2)
                                {
                                    ptr2[num4] = ptr7;
                                    ptr7++;
                                    if (ptr7 >= ptr5)
                                    {
                                        break;
                                    }
                                    continue;
                                }
                                flag2 = false;
                                ptr2[num4] = ptr7;
                                if (ptr7 - ptr6 > 0)
                                {
                                    uint num5 = (uint)(ptr7 - ptr6);
                                    switch (num5)
                                    {
                                        case 0u:
                                        case 1u:
                                        case 2u:
                                        case 3u:
                                        {
                                            Debug.Assert(ptr9 - 2 > ptr8);
                                            byte* num7 = ptr9 + -2;
                                            *num7 |= (byte)num5;
                                            break;
                                        }
                                        case 4u:
                                        case 5u:
                                        case 6u:
                                        case 7u:
                                        case 8u:
                                        case 9u:
                                        case 10u:
                                        case 11u:
                                        case 12u:
                                        case 13u:
                                        case 14u:
                                        case 15u:
                                        case 16u:
                                        case 17u:
                                        case 18u:
                                            *(ptr9++) = (byte)(num5 - 3);
                                            break;
                                        default:
                                        {
                                            uint num6 = num5 - 18;
                                            *(ptr9++) = 0;
                                            while (num6 > 255)
                                            {
                                                num6 -= 255;
                                                *(ptr9++) = 0;
                                            }
                                            Debug.Assert(num6 != 0);
                                            *(ptr9++) = (byte)num6;
                                            break;
                                        }
                                    }
                                    do
                                    {
                                        *(ptr9++) = *(ptr6++);
                                    } while (--num5 != 0);
                                }
                                Debug.Assert(ptr6 == ptr7);
                                ptr7 += 3;
                                if (
                                    ptr10[3] != *(ptr7++)
                                    || ptr10[4] != *(ptr7++)
                                    || ptr10[5] != *(ptr7++)
                                    || ptr10[6] != *(ptr7++)
                                    || ptr10[7] != *(ptr7++)
                                    || ptr10[8] != *(ptr7++)
                                )
                                {
                                    ptr7--;
                                    uint num8 = (uint)(ptr7 - ptr6);
                                    Debug.Assert(num8 >= 3);
                                    Debug.Assert(num8 <= 8);
                                    if (num3 <= 2048)
                                    {
                                        num3--;
                                        *(ptr9++) = (byte)((num8 - 1 << 5) | ((num3 & 7) << 2));
                                        *(ptr9++) = (byte)(num3 >> 3);
                                    }
                                    else if (num3 <= 16384)
                                    {
                                        num3--;
                                        *(ptr9++) = (byte)(0x20u | (num8 - 2));
                                        *(ptr9++) = (byte)((num3 & 0x3F) << 2);
                                        *(ptr9++) = (byte)(num3 >> 6);
                                    }
                                    else
                                    {
                                        num3 -= 16384;
                                        Debug.Assert(num3 != 0);
                                        Debug.Assert(num3 <= 32767);
                                        *(ptr9++) = (byte)(
                                            0x10u | ((num3 & 0x4000) >> 11) | (num8 - 2)
                                        );
                                        *(ptr9++) = (byte)((num3 & 0x3F) << 2);
                                        *(ptr9++) = (byte)(num3 >> 6);
                                    }
                                }
                                else
                                {
                                    for (
                                        byte* ptr11 = ptr10 + 8u + 1;
                                        ptr7 < ptr4 && *ptr11 == *ptr7;
                                        ptr7++
                                    )
                                    {
                                        ptr11++;
                                    }
                                    uint num8 = (uint)(ptr7 - ptr6);
                                    Debug.Assert(num8 > 8);
                                    if (num3 <= 16384)
                                    {
                                        num3--;
                                        if (num8 <= 33)
                                        {
                                            *(ptr9++) = (byte)(0x20u | (num8 - 2));
                                        }
                                        else
                                        {
                                            num8 -= 33;
                                            *(ptr9++) = 32;
                                            while (num8 > 255)
                                            {
                                                num8 -= 255;
                                                *(ptr9++) = 0;
                                            }
                                            Debug.Assert(num8 != 0);
                                            *(ptr9++) = (byte)num8;
                                        }
                                    }
                                    else
                                    {
                                        num3 -= 16384;
                                        Debug.Assert(num3 != 0);
                                        Debug.Assert(num3 <= 32767);
                                        if (num8 <= 9)
                                        {
                                            *(ptr9++) = (byte)(
                                                0x10u | ((num3 & 0x4000) >> 11) | (num8 - 2)
                                            );
                                        }
                                        else
                                        {
                                            num8 -= 9;
                                            *(ptr9++) = (byte)(0x10u | ((num3 & 0x4000) >> 11));
                                            while (num8 > 255)
                                            {
                                                num8 -= 255;
                                                *(ptr9++) = 0;
                                            }
                                            Debug.Assert(num8 != 0);
                                            *(ptr9++) = (byte)num8;
                                        }
                                    }
                                    *(ptr9++) = (byte)((num3 & 0x3F) << 2);
                                    *(ptr9++) = (byte)(num3 >> 6);
                                }
                                ptr6 = ptr7;
                                if (ptr7 < ptr5)
                                {
                                    continue;
                                }
                                break;
                            }
                            num = (uint)(ptr9 - ptr8);
                            num2 = (uint)(ptr4 - ptr6);
                        }
                    }
                }
            }
            if (num2 != 0)
            {
                uint num9 = (uint)src.Length - num2;
                if (num == 0 && num2 <= 238)
                {
                    dst[num++] = (byte)(17 + num2);
                }
                else
                {
                    switch (num2)
                    {
                        case 0u:
                        case 1u:
                        case 2u:
                        case 3u:
                            dst[num - 2] |= (byte)num2;
                            break;
                        case 4u:
                        case 5u:
                        case 6u:
                        case 7u:
                        case 8u:
                        case 9u:
                        case 10u:
                        case 11u:
                        case 12u:
                        case 13u:
                        case 14u:
                        case 15u:
                        case 16u:
                        case 17u:
                        case 18u:
                            dst[num++] = (byte)(num2 - 3);
                            break;
                        default:
                        {
                            uint num6 = num2 - 18;
                            dst[num++] = 0;
                            while (num6 > 255)
                            {
                                num6 -= 255;
                                dst[num++] = 0;
                            }
                            Debug.Assert(num6 != 0);
                            dst[num++] = (byte)num6;
                            break;
                        }
                    }
                }
                do
                {
                    dst[num++] = src[num9++];
                } while (--num2 != 0);
            }
            dst[num++] = 17;
            dst[num++] = 0;
            dst[num++] = 0;
            if (dst.Length != num)
            {
                byte[] array = new byte[num];
                Buffer.BlockCopy(dst, 0, array, 0, (int)num);
                dst = array;
            }
        }

        public static unsafe void Decompress(byte[] src, byte[] dst)
        {
            uint num = 0u;
            fixed (byte* ptr2 = src)
            {
                fixed (byte* ptr4 = dst)
                {
                    byte* ptr = null;
                    byte* ptr3 = ptr2 + src.Length;
                    byte* ptr5 = ptr4 + dst.Length;
                    byte* ptr6 = ptr2;
                    byte* ptr7 = ptr4;
                    bool flag = false;
                    bool flag2 = false;
                    bool flag3 = false;
                    bool flag4 = false;
                    bool flag5 = false;
                    bool flag6 = false;
                    if (*ptr6 > 17)
                    {
                        num = (uint)(*(ptr6++) - 17);
                        if (num < 4)
                        {
                            flag2 = true;
                        }
                        else
                        {
                            Debug.Assert(num != 0);
                            if (ptr5 - ptr7 < num)
                            {
                                throw new OverflowException("Output Overrun");
                            }
                            if (ptr3 - ptr6 < num + 1)
                            {
                                throw new OverflowException("Input Overrun");
                            }
                            do
                            {
                                *(ptr7++) = *(ptr6++);
                            } while (--num != 0);
                            flag5 = true;
                        }
                    }
                    while (!flag6 && ptr6 < ptr3)
                    {
                        if (!flag2 && !flag5)
                        {
                            num = *(ptr6++);
                            if (num >= 16)
                            {
                                flag = true;
                            }
                            else
                            {
                                if (num == 0)
                                {
                                    if (ptr3 - ptr6 < 1)
                                    {
                                        throw new OverflowException("Input Overrun");
                                    }
                                    while (*ptr6 == 0)
                                    {
                                        num += 255;
                                        ptr6++;
                                        if (ptr3 - ptr6 < 1)
                                        {
                                            throw new OverflowException("Input Overrun");
                                        }
                                    }
                                    num += (uint)(15 + *(ptr6++));
                                }
                                Debug.Assert(num != 0);
                                if (ptr5 - ptr7 < num + 3)
                                {
                                    throw new OverflowException("Output Overrun");
                                }
                                if (ptr3 - ptr6 < num + 4)
                                {
                                    throw new OverflowException("Input Overrun");
                                }
                                int num2 = 0;
                                while (num2 < 4)
                                {
                                    *ptr7 = *ptr6;
                                    num2++;
                                    ptr7++;
                                    ptr6++;
                                }
                                if (--num != 0)
                                {
                                    if (num >= 4)
                                    {
                                        do
                                        {
                                            num2 = 0;
                                            while (num2 < 4)
                                            {
                                                *ptr7 = *ptr6;
                                                num2++;
                                                ptr7++;
                                                ptr6++;
                                            }
                                            num -= 4;
                                        } while (num >= 4);
                                        if (num != 0)
                                        {
                                            do
                                            {
                                                *(ptr7++) = *(ptr6++);
                                            } while (--num != 0);
                                        }
                                    }
                                    else
                                    {
                                        do
                                        {
                                            *(ptr7++) = *(ptr6++);
                                        } while (--num != 0);
                                    }
                                }
                            }
                        }
                        if (!flag && !flag2)
                        {
                            flag5 = false;
                            num = *(ptr6++);
                            if (num >= 16)
                            {
                                flag = true;
                            }
                            else
                            {
                                ptr = ptr7 - 2049u;
                                ptr -= (int)(num >> 2);
                                ptr -= *(ptr6++) << 2;
                                if (ptr < ptr4 || ptr >= ptr7)
                                {
                                    throw new OverflowException("Lookbehind Overrun");
                                }
                                if (ptr5 - ptr7 < 3)
                                {
                                    throw new OverflowException("Output Overrun");
                                }
                                *(ptr7++) = *(ptr++);
                                *(ptr7++) = *(ptr++);
                                *(ptr7++) = *(ptr++);
                                flag3 = true;
                            }
                        }
                        flag = false;
                        do
                        {
                            switch (num)
                            {
                                default:
                                    ptr = ptr7 - 1;
                                    ptr -= (int)((num >> 2) & 7);
                                    ptr -= *(ptr6++) << 3;
                                    num = (num >> 5) - 1;
                                    if (ptr < ptr4 || ptr >= ptr7)
                                    {
                                        throw new OverflowException("Lookbehind Overrun");
                                    }
                                    if (ptr5 - ptr7 < num + 2)
                                    {
                                        throw new OverflowException("Output Overrun");
                                    }
                                    flag4 = true;
                                    break;
                                case 32u:
                                case 33u:
                                case 34u:
                                case 35u:
                                case 36u:
                                case 37u:
                                case 38u:
                                case 39u:
                                case 40u:
                                case 41u:
                                case 42u:
                                case 43u:
                                case 44u:
                                case 45u:
                                case 46u:
                                case 47u:
                                case 48u:
                                case 49u:
                                case 50u:
                                case 51u:
                                case 52u:
                                case 53u:
                                case 54u:
                                case 55u:
                                case 56u:
                                case 57u:
                                case 58u:
                                case 59u:
                                case 60u:
                                case 61u:
                                case 62u:
                                case 63u:
                                    num &= 0x1Fu;
                                    if (num == 0)
                                    {
                                        if (ptr3 - ptr6 < 1)
                                        {
                                            throw new OverflowException("Input Overrun");
                                        }
                                        while (*ptr6 == 0)
                                        {
                                            num += 255;
                                            ptr6++;
                                            if (ptr3 - ptr6 < 1)
                                            {
                                                throw new OverflowException("Input Overrun");
                                            }
                                        }
                                        num += (uint)(31 + *(ptr6++));
                                    }
                                    ptr = ptr7 - 1;
                                    ptr -= *(ushort*)ptr6 >> 2;
                                    ptr6 += 2;
                                    break;
                                case 16u:
                                case 17u:
                                case 18u:
                                case 19u:
                                case 20u:
                                case 21u:
                                case 22u:
                                case 23u:
                                case 24u:
                                case 25u:
                                case 26u:
                                case 27u:
                                case 28u:
                                case 29u:
                                case 30u:
                                case 31u:
                                    ptr = ptr7;
                                    ptr -= (int)((num & 8) << 11);
                                    num &= 7u;
                                    if (num == 0)
                                    {
                                        if (ptr3 - ptr6 < 1)
                                        {
                                            throw new OverflowException("Input Overrun");
                                        }
                                        while (*ptr6 == 0)
                                        {
                                            num += 255;
                                            ptr6++;
                                            if (ptr3 - ptr6 < 1)
                                            {
                                                throw new OverflowException("Input Overrun");
                                            }
                                        }
                                        num += (uint)(7 + *(ptr6++));
                                    }
                                    ptr -= *(ushort*)ptr6 >> 2;
                                    ptr6 += 2;
                                    if (ptr == ptr7)
                                    {
                                        flag6 = true;
                                    }
                                    else
                                    {
                                        ptr -= 16384;
                                    }
                                    break;
                                case 0u:
                                case 1u:
                                case 2u:
                                case 3u:
                                case 4u:
                                case 5u:
                                case 6u:
                                case 7u:
                                case 8u:
                                case 9u:
                                case 10u:
                                case 11u:
                                case 12u:
                                case 13u:
                                case 14u:
                                case 15u:
                                    ptr = ptr7 - 1;
                                    ptr -= (int)(num >> 2);
                                    ptr -= *(ptr6++) << 2;
                                    if (ptr < ptr4 || ptr >= ptr7)
                                    {
                                        throw new OverflowException("Lookbehind Overrun");
                                    }
                                    if (ptr5 - ptr7 < 2)
                                    {
                                        throw new OverflowException("Output Overrun");
                                    }
                                    *(ptr7++) = *(ptr++);
                                    *(ptr7++) = *(ptr++);
                                    flag3 = true;
                                    break;
                            }
                            if (!flag6 && !flag3 && !flag4)
                            {
                                if (ptr < ptr4 || ptr >= ptr7)
                                {
                                    throw new OverflowException("Lookbehind Overrun");
                                }
                                Debug.Assert(num != 0);
                                if (ptr5 - ptr7 < num + 2)
                                {
                                    throw new OverflowException("Output Overrun");
                                }
                            }
                            if (!flag6 && num >= 6 && ptr7 - ptr >= 4 && !flag3 && !flag4)
                            {
                                int num2 = 0;
                                while (num2 < 4)
                                {
                                    *ptr7 = *ptr;
                                    num2++;
                                    ptr7++;
                                    ptr++;
                                }
                                num -= 2;
                                do
                                {
                                    num2 = 0;
                                    while (num2 < 4)
                                    {
                                        *ptr7 = *ptr;
                                        num2++;
                                        ptr7++;
                                        ptr++;
                                    }
                                    num -= 4;
                                } while (num >= 4);
                                if (num != 0)
                                {
                                    do
                                    {
                                        *(ptr7++) = *(ptr++);
                                    } while (--num != 0);
                                }
                            }
                            else if (!flag6 && !flag3)
                            {
                                flag4 = false;
                                *(ptr7++) = *(ptr++);
                                *(ptr7++) = *(ptr++);
                                do
                                {
                                    *(ptr7++) = *(ptr++);
                                } while (--num != 0);
                            }
                            if (!flag6 && !flag2)
                            {
                                flag3 = false;
                                num = ptr6[-2] & 3u;
                                if (num == 0)
                                {
                                    break;
                                }
                            }
                            if (flag6)
                            {
                                continue;
                            }
                            flag2 = false;
                            Debug.Assert(num != 0);
                            Debug.Assert(num < 4);
                            if (ptr5 - ptr7 < num)
                            {
                                throw new OverflowException("Output Overrun");
                            }
                            if (ptr3 - ptr6 < num + 1)
                            {
                                throw new OverflowException("Input Overrun");
                            }
                            *(ptr7++) = *(ptr6++);
                            if (num > 1)
                            {
                                *(ptr7++) = *(ptr6++);
                                if (num > 2)
                                {
                                    *(ptr7++) = *(ptr6++);
                                }
                            }
                            num = *(ptr6++);
                        } while (!flag6 && ptr6 < ptr3);
                    }
                    if (!flag6)
                    {
                        throw new OverflowException("EOF Marker Not Found");
                    }
                    Debug.Assert(num == 1);
                    if (ptr6 > ptr3)
                    {
                        throw new OverflowException("Input Overrun");
                    }
                    if (ptr6 < ptr3)
                    {
                        throw new OverflowException("Input Not Consumed");
                    }
                }
            }
        }

        private static unsafe uint a(byte* A_0)
        {
            return a(a(33u, a(A_0, 5, 5, 6)) >> 5, 0);
        }

        private static uint a(uint A_0)
        {
            return (A_0 & 0x7FFu) ^ 0x201Fu;
        }

        private static uint a(uint A_0, byte A_1)
        {
            return (A_0 & (uint)(16383 >>> (int)A_1)) << (int)A_1;
        }

        private static uint a(uint A_0, uint A_1)
        {
            return A_0 * A_1;
        }

        private static unsafe uint a(byte* A_0, byte A_1, byte A_2)
        {
            return (uint)((((A_0[2] << (int)A_2) ^ A_0[1]) << (int)A_1) ^ *A_0);
        }

        private static unsafe uint a(byte* A_0, byte A_1, byte A_2, byte A_3)
        {
            return (a(A_0 + 1, A_2, A_3) << (int)A_1) ^ *A_0;
        }

        public static byte[] DecompressBytes(byte[] array)
        {
            int num = BitConverter.ToInt32(array, 0);
            byte[] array2 = new byte[array.Length - 4 - 1 + 1];
            Array.Copy(array, 4, array2, 0, array2.Length);
            byte[] array3 = new byte[num - 1 + 1];
            Array.Clear(array3, 0, array3.Length);
            Decompress(array2, array3);
            Array.Resize(ref array, array3.Length);
            Array.Clear(array, 0, array.Length);
            Array.Copy(array3, array, array.Length);

            return array;
        }

        public static byte[] CompressBytes(byte[] array)
        {
            byte[] dst = new byte[0];
            Compress(array, out dst);
            int value3 = array.Length;
            int num = dst.Length;
            Array.Clear(array, 0, array.Length);
            Array.Resize(ref array, dst.Length + 4);
            byte[] bytes6 = BitConverter.GetBytes(value3);
            Array.Copy(bytes6, array, bytes6.Length);
            Array.Copy(dst, 0, array, 4, dst.Length);

            return array;
        }

        public static int TheAnswer()
        {
            return 42;
        }

        // dotnet new console --framework net8.0
        // dotnet build --configuration Release
    }
}
